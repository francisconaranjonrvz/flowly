# Tests de tableros, columnas y permisos (vistas con templates + sesión).

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from boards.models import Board, BoardMembership, Column

User = get_user_model()


class BoardViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234')

    def login(self, user):
        password = 'alicepass1' if user.username == 'alice' else 'bobpass1234'
        self.client.login(username=user.username, password=password)

    # --- Acceso sin autenticar ---

    def test_home_requires_login(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    # --- Crear y listar tableros ---

    def test_create_board_with_default_columns(self):
        self.login(self.alice)
        resp = self.client.post(reverse('board-create'), {'name': 'TFG', 'description': 'x'})
        board = Board.objects.get(name='TFG')
        self.assertRedirects(resp, reverse('board-detail', args=[board.pk]))
        self.assertEqual(board.owner, self.alice)
        self.assertEqual(list(board.columns.order_by('order').values_list('title', flat=True)),
                          ['Pendiente', 'En Progreso', 'Completado'])

    def test_home_lists_only_own_and_member_boards(self):
        Board.objects.create(owner=self.alice, name='Solo Alice')
        shared = Board.objects.create(owner=self.bob, name='Shared')
        BoardMembership.objects.create(user=self.alice, board=shared)
        Board.objects.create(owner=self.bob, name='Solo Bob')

        self.login(self.alice)
        resp = self.client.get(reverse('home'))
        names = {b.name for b in resp.context['boards']}
        self.assertEqual(names, {'Solo Alice', 'Shared'})

    # --- Aislamiento entre usuarios ---

    def test_other_user_cannot_view_board(self):
        board = Board.objects.create(owner=self.alice, name='Solo Alice')
        self.login(self.bob)
        resp = self.client.get(reverse('board-detail', args=[board.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_only_owner_can_delete_board(self):
        board = Board.objects.create(owner=self.alice, name='B')
        self.login(self.bob)
        resp = self.client.post(reverse('board-delete', args=[board.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Board.objects.filter(pk=board.pk).exists())

        self.login(self.alice)
        resp = self.client.post(reverse('board-delete', args=[board.pk]))
        self.assertRedirects(resp, reverse('home'))
        self.assertFalse(Board.objects.filter(pk=board.pk).exists())

    def test_member_can_view_board_but_not_delete(self):
        board = Board.objects.create(owner=self.alice, name='Shared')
        BoardMembership.objects.create(user=self.bob, board=board)

        self.login(self.bob)
        resp = self.client.get(reverse('board-detail', args=[board.pk]))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(reverse('board-delete', args=[board.pk]))
        self.assertEqual(resp.status_code, 403)

    # --- Columnas + reordenar ---

    def test_columns_get_sequential_orders(self):
        self.login(self.alice)
        board = Board.objects.create(owner=self.alice, name='B')
        for title in ('A', 'B', 'C'):
            self.client.post(reverse('column-create', args=[board.pk]), {'title': title})
        cols = list(board.columns.order_by('order'))
        self.assertEqual([c.order for c in cols], [0, 1, 2])

    def test_column_move_reorders(self):
        self.login(self.alice)
        board = Board.objects.create(owner=self.alice, name='B')
        c1 = Column.objects.create(board=board, title='A', order=0)
        c2 = Column.objects.create(board=board, title='B', order=1)
        c3 = Column.objects.create(board=board, title='C', order=2)

        resp = self.client.post(
            reverse('column-move', args=[board.pk]),
            data=json.dumps({'column_id': c3.id, 'order': 0}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        c1.refresh_from_db(); c2.refresh_from_db(); c3.refresh_from_db()
        self.assertEqual([c3.order, c1.order, c2.order], [0, 1, 2])

    def test_other_user_cannot_move_column(self):
        board = Board.objects.create(owner=self.alice, name='B')
        col = Column.objects.create(board=board, title='A', order=0)
        self.login(self.bob)
        resp = self.client.post(
            reverse('column-move', args=[board.pk]),
            data=json.dumps({'column_id': col.id, 'order': 0}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 403)


class DesignSystemTests(TestCase):
    """Sistema de diseño Flowly (Paso 3): assets, identidad y tema."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='dani', password='danipass1')

    def test_base_layout_ships_design_assets_and_identity(self):
        self.client.login(username='dani', password='danipass1')
        board = Board.objects.create(owner=self.user, name='Tablero')
        resp = self.client.get(reverse('board-detail', args=[board.pk]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Hojas de estilo del sistema de diseño + utilidades Tailwind
        self.assertIn('design-system', html)
        self.assertIn('tailwind.build', html)
        # Librerías de interacción vendorizadas (sin CDN)
        self.assertIn('vendor/htmx.min', html)
        self.assertIn('vendor/alpine.min', html)
        # App-shell: marca data-brand + navegación lateral
        self.assertIn('data-brand=', html)
        self.assertIn('Flowly', html)
        self.assertIn('Tableros', html)
        # Script anti-FOUC que fija el tema antes del primer paint
        self.assertIn("setAttribute('data-theme'", html)


class ColumnRenameHtmxTests(TestCase):
    """La renombrada de columna se enriquece con HTMX pero degrada a redirect."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='eva', password='evapass1234')
        cls.board = Board.objects.create(owner=cls.user, name='B')
        cls.col = Column.objects.create(board=cls.board, title='To Do', order=0)

    def setUp(self):
        self.client.login(username='eva', password='evapass1234')

    def test_htmx_request_returns_partial_not_full_page(self):
        resp = self.client.post(
            reverse('column-rename', args=[self.board.pk, self.col.pk]),
            {'title': 'En curso'},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Solo el parcial del título, no el layout completo
        self.assertIn('En curso', html)
        self.assertIn(f'id="column-title-{self.col.pk}"', html)
        self.assertNotIn('<!DOCTYPE', html)
        self.assertNotIn('topbar__brand', html)
        self.col.refresh_from_db()
        self.assertEqual(self.col.title, 'En curso')

    def test_plain_request_redirects_to_board(self):
        resp = self.client.post(
            reverse('column-rename', args=[self.board.pk, self.col.pk]),
            {'title': 'Hecho'},
        )
        self.assertRedirects(resp, reverse('board-detail', args=[self.board.pk]))
        self.col.refresh_from_db()
        self.assertEqual(self.col.title, 'Hecho')


class CalendarViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from datetime import date
        from tasks.models import Card

        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.board = Board.objects.create(name='Cal', owner=cls.alice)
        cls.col = Column.objects.create(board=cls.board, title='To Do', order=0)
        cls.in_month = Card.objects.create(
            column=cls.col, title='Entrega mensual', order=0,
            due_date=date(2026, 6, 15), priority=4,
        )
        cls.other_month = Card.objects.create(
            column=cls.col, title='Fuera de mes', order=1,
            due_date=date(2026, 9, 1), priority=1,
        )
        cls.no_due = Card.objects.create(column=cls.col, title='Sin fecha', order=2)

    def test_calendar_requires_login(self):
        resp = self.client.get(reverse('calendario'))
        self.assertEqual(resp.status_code, 302)

    def test_calendar_shows_card_in_month(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.get(reverse('calendario'), {'year': 2026, 'month': 6})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('Junio 2026', html)
        self.assertIn('Entrega mensual', html)
        self.assertNotIn('Fuera de mes', html)
        self.assertNotIn('Sin fecha', html)

    def test_calendar_priority_filter(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.get(reverse('calendario'), {'year': 2026, 'month': 6, 'priority': 1})
        self.assertNotIn('Entrega mensual', resp.content.decode())

    def test_calendar_invalid_month_falls_back(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.get(reverse('calendario'), {'year': 'x', 'month': '99'})
        self.assertEqual(resp.status_code, 200)


class TeamViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from organizations.models import Organization, OrganizationMembership
        from tasks.models import Card

        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234')
        cls.org = Organization.objects.create(name='Acme')
        OrganizationMembership.objects.create(
            organization=cls.org, user=cls.alice,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            organization=cls.org, user=cls.bob,
            role=OrganizationMembership.Role.MEMBER,
        )
        cls.board = Board.objects.create(name='B', owner=cls.alice, organization=cls.org)
        BoardMembership.objects.create(board=cls.board, user=cls.bob)
        cls.todo = Column.objects.create(board=cls.board, title='Pendiente', order=0)
        cls.done = Column.objects.create(board=cls.board, title='Completado', order=1)
        # 9 tareas activas para bob -> supera capacidad (8) -> saturado
        for i in range(9):
            card = Card.objects.create(column=cls.todo, title=f'T{i}', order=i)
            card.assignees.add(cls.bob)
        # 1 tarea terminada (no cuenta como carga)
        done_card = Card.objects.create(column=cls.done, title='Done', order=0)
        done_card.assignees.add(cls.bob)

    def _activate_org(self):
        session = self.client.session
        session['active_org_id'] = self.org.id
        session.save()

    def test_team_requires_login(self):
        resp = self.client.get(reverse('equipo'))
        self.assertEqual(resp.status_code, 302)

    def test_team_lists_members_and_overload(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate_org()
        resp = self.client.get(reverse('equipo'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('alice', html)
        self.assertIn('bob', html)
        # bob con 9 activas (>85% de 8) debe marcarse como saturado
        self.assertIn('Saturado', html)

    def test_done_column_excluded_from_load(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate_org()
        resp = self.client.get(reverse('equipo'))
        # bob: 9 activas, no 10 (la de "Completado" no cuenta)
        self.assertContains(resp, '9/8')


class BoardViewModesTests(TestCase):
    """El parámetro ?view= alterna kanban/lista/tabla/calendario."""

    @classmethod
    def setUpTestData(cls):
        from tasks.models import Card

        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.board = Board.objects.create(name='Proj', owner=cls.alice)
        cls.col = Column.objects.create(board=cls.board, title='To Do', order=0)
        Card.objects.create(column=cls.col, title='Tarea visible', order=0)

    def setUp(self):
        self.client.login(username='alice', password='alicepass1')

    def test_kanban_default_includes_board_js(self):
        resp = self.client.get(reverse('board-detail', args=[self.board.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'board.js')
        self.assertContains(resp, 'Tarea visible')

    def test_list_view_no_board_js(self):
        resp = self.client.get(reverse('board-detail', args=[self.board.id]), {'view': 'list'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tarea visible')
        self.assertNotContains(resp, 'board.js')

    def test_table_view_renders(self):
        resp = self.client.get(reverse('board-detail', args=[self.board.id]), {'view': 'table'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<table')
        self.assertContains(resp, 'Tarea visible')
        self.assertNotContains(resp, 'board.js')

    def test_calendar_view_renders(self):
        resp = self.client.get(reverse('board-detail', args=[self.board.id]), {'view': 'calendar'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'view=kanban')  # selector de vista presente

    def test_invalid_view_falls_back_to_kanban(self):
        resp = self.client.get(reverse('board-detail', args=[self.board.id]), {'view': 'nope'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'board.js')


class BoardColumnsPollTests(TestCase):
    """La vista de polling del kanban (tiempo real) respeta permisos."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234')
        cls.board = Board.objects.create(owner=cls.alice, name='B')
        Column.objects.create(board=cls.board, title='To Do', order=0)

    def test_owner_gets_columns_partial(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.get(reverse('board-columns', args=[self.board.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'To Do')

    def test_non_member_forbidden(self):
        self.client.login(username='bob', password='bobpass1234')
        resp = self.client.get(reverse('board-columns', args=[self.board.pk]))
        self.assertEqual(resp.status_code, 403)
