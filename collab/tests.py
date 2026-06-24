# Tests de colaboración v4: notificaciones, chat, presencia, office, búsqueda.

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from boards.models import Board, BoardMembership, Column
from collab.models import Channel, Message, Notification, notify
from organizations.models import Organization, OrganizationMembership
from tasks.models import Card

User = get_user_model()


class NotificationOpenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = User.objects.create_user(username='alice', password='alicepass1')
        cls.org = Organization.objects.create(name='Acme')
        OrganizationMembership.objects.create(organization=cls.org, user=cls.a, role=OrganizationMembership.Role.OWNER)
        cls.other_org = Organization.objects.create(name='Otra')

    def _activate(self, org):
        s = self.client.session
        s['active_org_id'] = org.id
        s.save()

    def test_open_marks_read_and_redirects(self):
        n = Notification.objects.create(recipient=self.a, organization=self.org, verb='hola', url='/perfil/')
        self.client.login(username='alice', password='alicepass1')
        self._activate(self.org)
        resp = self.client.get(reverse('notification-open', args=[n.id]))
        self.assertRedirects(resp, '/perfil/', fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertFalse(n.unread)

    def test_open_other_user_404(self):
        b = User.objects.create_user(username='bob', password='bobpass1234')
        n = Notification.objects.create(recipient=b, organization=self.org, verb='x')
        self.client.login(username='alice', password='alicepass1')
        self._activate(self.org)
        self.assertEqual(self.client.get(reverse('notification-open', args=[n.id])).status_code, 404)

    def test_cross_org_isolation(self):
        """Una notificación de otra organización NO se ve ni se abre desde la activa."""
        n = Notification.objects.create(recipient=self.a, organization=self.other_org, verb='secreta', url='/perfil/')
        self.client.login(username='alice', password='alicepass1')
        self._activate(self.org)
        # No aparece en la bandeja de la org activa…
        inbox = self.client.get(reverse('notificaciones'))
        self.assertNotContains(inbox, 'secreta')
        # …y abrir su id da 404 (no se salta de tenant).
        self.assertEqual(self.client.get(reverse('notification-open', args=[n.id])).status_code, 404)


class ChannelChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='alice', password='alicepass1')
        cls.member = User.objects.create_user(username='bob', password='bobpass1234')
        cls.org = Organization.objects.create(name='Acme')
        OrganizationMembership.objects.create(organization=cls.org, user=cls.owner, role=OrganizationMembership.Role.OWNER)
        OrganizationMembership.objects.create(organization=cls.org, user=cls.member, role=OrganizationMembership.Role.MEMBER)

    def _activate(self):
        s = self.client.session
        s['active_org_id'] = self.org.id
        s.save()

    def test_general_autocreated(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        resp = self.client.get(reverse('chat'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Channel.objects.filter(organization=self.org, is_general=True).exists())

    def test_create_and_send_and_mention(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        self.client.post(reverse('channel-create'), {'name': 'random'})
        ch = Channel.objects.get(organization=self.org, slug='random')
        self.client.post(reverse('channel-send', args=[ch.id]), {'body': 'eh @bob ven'})
        self.assertEqual(ch.messages.count(), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.member, verb__icontains='#random').exists())


class NotifyHelperTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = User.objects.create_user(username='alice', password='alicepass1')
        cls.b = User.objects.create_user(username='bob', password='bobpass1234')

    def test_notify_creates_for_other(self):
        notify(self.b, verb='hola', actor=self.a)
        self.assertEqual(self.b.notifications.count(), 1)

    def test_notify_skips_self(self):
        notify(self.a, verb='yo mismo', actor=self.a)
        self.assertEqual(self.a.notifications.count(), 0)

    def test_notify_none_recipient(self):
        self.assertIsNone(notify(None, verb='x', actor=self.a))


class PresenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = User.objects.create_user(username='alice', password='alicepass1')

    def test_ping_updates_last_seen(self):
        self.assertIsNone(self.a.last_seen)
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.get(reverse('presence-ping'))
        self.assertEqual(resp.status_code, 204)
        self.a.refresh_from_db()
        self.assertIsNotNone(self.a.last_seen)
        self.assertEqual(self.a.presence, 'online')


class ChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='alice', password='alicepass1')
        cls.member = User.objects.create_user(username='bob', password='bobpass1234')
        cls.outsider = User.objects.create_user(username='carol', password='carolpass12')
        cls.board = Board.objects.create(name='B', owner=cls.owner)
        BoardMembership.objects.create(board=cls.board, user=cls.member)

    def test_send_creates_message(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.post(reverse('chat-send', args=[self.board.id]), {'body': 'hola'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.board.messages.count(), 1)

    def test_outsider_forbidden(self):
        self.client.login(username='carol', password='carolpass12')
        resp = self.client.post(reverse('chat-send', args=[self.board.id]), {'body': 'x'})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.board.messages.count(), 0)

    def test_mention_notifies_member(self):
        self.client.login(username='alice', password='alicepass1')
        self.client.post(reverse('chat-send', args=[self.board.id]), {'body': 'eh @bob mira esto'})
        self.assertTrue(Notification.objects.filter(recipient=self.member, verb__icontains='mencionó').exists())


class SearchAndMyTasksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from organizations.models import Organization, OrganizationMembership
        cls.user = User.objects.create_user(username='alice', password='alicepass1')
        cls.org = Organization.objects.create(name='Acme')
        OrganizationMembership.objects.create(
            organization=cls.org, user=cls.user, role=OrganizationMembership.Role.OWNER)
        cls.board = Board.objects.create(name='Marketing', owner=cls.user, organization=cls.org)
        cls.col = Column.objects.create(board=cls.board, title='To Do', order=0)
        cls.card = Card.objects.create(column=cls.col, title='Lanzar campaña', order=0)
        cls.card.assignees.add(cls.user)

    def _activate(self):
        s = self.client.session
        s['active_org_id'] = self.org.id
        s.save()

    def test_search_finds_card_and_board(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        resp = self.client.get(reverse('buscar'), {'q': 'campaña'})
        self.assertContains(resp, 'Lanzar campaña')
        resp2 = self.client.get(reverse('buscar'), {'q': 'Marketing'})
        self.assertContains(resp2, 'Marketing')

    def test_mis_tareas_lists_assigned(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        resp = self.client.get(reverse('mis-tareas'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Lanzar campaña')

    def test_office_renders(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        self.assertEqual(self.client.get(reverse('office')).status_code, 200)
        room = self.client.get(reverse('office-room'))
        self.assertContains(room, 'alice')

    def test_search_suggest(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        resp = self.client.get(reverse('search-suggest'), {'q': 'camp'})
        self.assertContains(resp, 'Lanzar campaña')

    def test_office_customize_persists_and_validates(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        self.client.post(reverse('office-customize'), {
            'char_skin': '2', 'char_hair': '1', 'char_hair_style': '0', 'char_shirt': '999',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.char_skin, 2)
        self.assertIsNone(self.user.char_shirt)  # índice inválido -> None

    def test_member_profile_and_404(self):
        self.client.login(username='alice', password='alicepass1')
        self._activate()
        ok = self.client.get(reverse('equipo-member', args=[self.user.id]))
        self.assertEqual(ok.status_code, 200)
        outsider = User.objects.create_user(username='zoe', password='zoepass1234')
        self.assertEqual(self.client.get(reverse('equipo-member', args=[outsider.id])).status_code, 404)
