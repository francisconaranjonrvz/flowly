# Tests de subtareas, comentarios, progreso y asignados (Fase 2).

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from boards.models import Board, BoardMembership, Column, Label
from tasks.models import Card, Comment, Subtask

User = get_user_model()


class CardCreateRichTests(TestCase):
    """Crear tarjeta con campos extra (descripción, etiquetas, asignados)."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234')
        cls.carol = User.objects.create_user(username='carol', password='carolpass12')
        cls.board = Board.objects.create(name='B', owner=cls.alice)
        BoardMembership.objects.create(board=cls.board, user=cls.bob)
        cls.col = Column.objects.create(board=cls.board, title='To Do', order=0)
        cls.label = Label.objects.create(board=cls.board, name='Bug', color='#ef4444')

    def test_create_with_labels_and_assignees(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.post(reverse('card-create', args=[self.board.id]), {
            'column': self.col.id, 'title': 'Nueva', 'description': 'desc',
            'priority': 3, 'labels': [self.label.id], 'assignees': [self.bob.id],
        })
        self.assertEqual(resp.status_code, 302)
        card = Card.objects.get(title='Nueva')
        self.assertEqual(card.description, 'desc')
        self.assertIn(self.label, card.labels.all())
        self.assertIn(self.bob, card.assignees.all())
        self.assertEqual(card.assignee, self.bob)  # FK sincronizado

    def test_create_ignores_non_member_assignee(self):
        self.client.login(username='alice', password='alicepass1')
        self.client.post(reverse('card-create', args=[self.board.id]), {
            'column': self.col.id, 'title': 'X', 'assignees': [self.carol.id],
        })
        card = Card.objects.get(title='X')
        self.assertFalse(card.assignees.filter(id=self.carol.id).exists())


class TaskDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234')
        cls.carol = User.objects.create_user(username='carol', password='carolpass12')
        cls.board = Board.objects.create(name='Proyecto', owner=cls.alice)
        BoardMembership.objects.create(board=cls.board, user=cls.bob)
        cls.column = Column.objects.create(board=cls.board, title='To Do', order=0)
        cls.card = Card.objects.create(column=cls.column, title='Tarea 1', order=0)

    def login(self, user):
        passwords = {'alice': 'alicepass1', 'bob': 'bobpass1234', 'carol': 'carolpass12'}
        self.client.login(username=user.username, password=passwords[user.username])

    def url(self, name, **kwargs):
        kwargs.setdefault('board_id', self.board.id)
        kwargs.setdefault('card_id', self.card.id)
        return reverse(name, kwargs=kwargs)

    # --- Progreso ---

    def test_progress_empty(self):
        self.assertEqual(self.card.progress, 0)
        self.assertEqual(self.card.subtask_total, 0)

    def test_progress_calculation(self):
        Subtask.objects.create(card=self.card, title='a', is_done=True, order=0)
        Subtask.objects.create(card=self.card, title='b', is_done=False, order=1)
        self.assertEqual(self.card.subtask_total, 2)
        self.assertEqual(self.card.subtask_done, 1)
        self.assertEqual(self.card.progress, 50)

    # --- Subtareas (HTMX) ---

    def test_subtask_create_and_toggle(self):
        self.login(self.alice)
        resp = self.client.post(self.url('subtask-create'), {'title': 'Diseño'})
        self.assertEqual(resp.status_code, 200)
        subtask = self.card.subtasks.get()
        self.assertEqual(subtask.title, 'Diseño')
        self.assertFalse(subtask.is_done)

        resp = self.client.post(self.url('subtask-toggle', subtask_id=subtask.id))
        self.assertEqual(resp.status_code, 200)
        subtask.refresh_from_db()
        self.assertTrue(subtask.is_done)

    def test_subtask_delete(self):
        self.login(self.alice)
        subtask = Subtask.objects.create(card=self.card, title='x', order=0)
        resp = self.client.post(self.url('subtask-delete', subtask_id=subtask.id))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.card.subtasks.exists())

    def test_subtask_requires_access(self):
        self.login(self.carol)  # ni dueña ni miembro
        resp = self.client.post(self.url('subtask-create'), {'title': 'hack'})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(self.card.subtasks.exists())

    # --- Comentarios (HTMX) ---

    def test_comment_create(self):
        self.login(self.bob)
        resp = self.client.post(self.url('comment-create'), {'body': 'Buen trabajo'})
        self.assertEqual(resp.status_code, 200)
        comment = self.card.comments.get()
        self.assertEqual(comment.body, 'Buen trabajo')
        self.assertEqual(comment.author, self.bob)

    def test_comment_delete_own(self):
        self.login(self.bob)
        comment = Comment.objects.create(card=self.card, author=self.bob, body='hola')
        resp = self.client.post(self.url('comment-delete', comment_id=comment.id))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.card.comments.exists())

    def test_comment_delete_others_forbidden_for_member(self):
        # bob (miembro) no puede borrar el comentario de alice (no es dueño)
        comment = Comment.objects.create(card=self.card, author=self.alice, body='mío')
        self.login(self.bob)
        self.client.post(self.url('comment-delete', comment_id=comment.id))
        self.assertTrue(self.card.comments.filter(id=comment.id).exists())

    def test_comment_delete_by_board_owner(self):
        # alice (dueña del tablero) sí puede borrar el comentario de bob
        comment = Comment.objects.create(card=self.card, author=self.bob, body='de bob')
        self.login(self.alice)
        self.client.post(self.url('comment-delete', comment_id=comment.id))
        self.assertFalse(self.card.comments.filter(id=comment.id).exists())

    # --- Asignados (formulario de edición) ---

    def test_edit_sets_assignees_and_syncs_assignee(self):
        self.login(self.alice)
        resp = self.client.post(self.url('card-edit'), {
            'title': 'Tarea 1',
            'description': '',
            'priority': 0,
            'column': self.column.id,
            'assignees': [self.alice.id, self.bob.id],
        })
        self.assertEqual(resp.status_code, 302)
        self.card.refresh_from_db()
        self.assertEqual(set(self.card.assignees.values_list('id', flat=True)),
                         {self.alice.id, self.bob.id})
        # FK assignee sincronizado con el primer asignado
        self.assertIn(self.card.assignee_id, {self.alice.id, self.bob.id})

    def test_edit_ignores_non_member_assignee(self):
        self.login(self.alice)
        self.client.post(self.url('card-edit'), {
            'title': 'Tarea 1', 'description': '', 'priority': 0,
            'column': self.column.id, 'assignees': [self.carol.id],
        })
        self.card.refresh_from_db()
        self.assertFalse(self.card.assignees.filter(id=self.carol.id).exists())
