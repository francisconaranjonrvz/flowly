# Tests de perfil de usuario (Fase 5) + apariencia y avatar (Refinamientos v2).

import tempfile
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from users.validators import MaxFileSizeValidator
from django.core.exceptions import ValidationError

User = get_user_model()


def _png_bytes(size=(12, 12), color='red'):
    buf = BytesIO()
    Image.new('RGB', size, color).save(buf, 'PNG')
    return buf.getvalue()


class ProfileViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1', email='alice@example.com')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234', email='bob@example.com')

    def test_perfil_requires_login(self):
        resp = self.client.get(reverse('perfil'))
        self.assertEqual(resp.status_code, 302)

    def test_perfil_renders_form(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.get(reverse('perfil'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Mi perfil', resp.content.decode())

    def test_perfil_update_saves(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.post(reverse('perfil'), {
            'first_name': 'Alicia', 'last_name': 'García',
            'email': 'alice@example.com', 'bio': 'Hola mundo', 'avatar': '',
        })
        self.assertRedirects(resp, reverse('perfil'))
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.first_name, 'Alicia')
        self.assertEqual(self.alice.bio, 'Hola mundo')

    def test_perfil_rejects_duplicate_email(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.post(reverse('perfil'), {
            'first_name': '', 'last_name': '',
            'email': 'bob@example.com', 'bio': '', 'avatar': '',
        })
        self.assertEqual(resp.status_code, 200)  # re-render con error
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, 'alice@example.com')


class AppearanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1')

    def test_appearance_requires_login(self):
        resp = self.client.post(reverse('perfil-apariencia'), {'theme_brand': 'nsw'})
        self.assertEqual(resp.status_code, 302)

    def test_appearance_persists_valid(self):
        self.client.login(username='alice', password='alicepass1')
        resp = self.client.post(reverse('perfil-apariencia'), {'theme_brand': 'nsw', 'theme_mode': 'dark'})
        self.assertRedirects(resp, reverse('perfil'))
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.theme_brand, 'nsw')
        self.assertEqual(self.alice.theme_mode, 'dark')

    def test_appearance_rejects_invalid(self):
        self.client.login(username='alice', password='alicepass1')
        self.client.post(reverse('perfil-apariencia'), {'theme_brand': 'hacker', 'theme_mode': 'neon'})
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.theme_brand, '')  # inválido -> heredar
        self.assertEqual(self.alice.theme_mode, '')

    def test_user_brand_sets_data_brand(self):
        self.client.login(username='alice', password='alicepass1')
        self.alice.theme_brand = 'nsw'
        self.alice.save(update_fields=['theme_brand'])
        resp = self.client.get(reverse('perfil'))
        self.assertContains(resp, 'data-brand="nsw"')


class AvatarUploadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1', email='a@x.com')

    def test_max_file_size_validator(self):
        validator = MaxFileSizeValidator(100)
        small = SimpleUploadedFile('s.png', b'x' * 50, content_type='image/png')
        validator(small)  # no lanza
        big = SimpleUploadedFile('b.png', b'x' * 200, content_type='image/png')
        with self.assertRaises(ValidationError):
            validator(big)

    def test_upload_valid_png(self):
        self.client.login(username='alice', password='alicepass1')
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                img = SimpleUploadedFile('avatar.png', _png_bytes(), content_type='image/png')
                resp = self.client.post(reverse('perfil'), {
                    'first_name': '', 'last_name': '', 'email': 'a@x.com',
                    'bio': '', 'avatar': img,
                })
                self.assertRedirects(resp, reverse('perfil'))
                self.alice.refresh_from_db()
                self.assertTrue(self.alice.avatar)
                self.assertIn('avatars/', self.alice.avatar.name)

    def test_upload_rejects_wrong_extension(self):
        self.client.login(username='alice', password='alicepass1')
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                bad = SimpleUploadedFile('avatar.gif', _png_bytes(), content_type='image/gif')
                resp = self.client.post(reverse('perfil'), {
                    'first_name': '', 'last_name': '', 'email': 'a@x.com',
                    'bio': '', 'avatar': bad,
                })
                self.assertEqual(resp.status_code, 200)  # re-render con error
                self.alice.refresh_from_db()
                self.assertFalse(self.alice.avatar)


class DemoSandboxTests(TestCase):
    """Acceso demo sin credenciales: un sandbox aislado por visitante."""

    def _enter_demo(self, client=None):
        return (client or self.client).post(reverse('demo-login'))

    def test_get_renders_without_creating(self):
        resp = self.client.get(reverse('demo-login'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'noindex')
        self.assertFalse(User.objects.filter(is_demo=True).exists())

    def test_post_creates_seeded_sandbox_and_logs_in(self):
        from boards.models import Board
        from collab.models import Message, Notification

        resp = self._enter_demo()
        visitor = User.objects.get(is_demo=True, first_name='Invitado')
        board = Board.objects.filter(owner=visitor).order_by('id').first()
        self.assertRedirects(resp, reverse('board-detail', args=[board.id]))
        self.assertEqual(int(self.client.session['_auth_user_id']), visitor.pk)
        self.assertFalse(visitor.has_usable_password())

        self.assertEqual(Board.objects.filter(owner=visitor).count(), 2)
        self.assertEqual(board.organization.name, 'Flowly Demo')
        mates = User.objects.filter(username__startswith=f'{visitor.username}-')
        self.assertEqual(mates.count(), 2)
        self.assertTrue(all(m.is_demo for m in mates))
        self.assertTrue(Message.objects.filter(board=board).exists())
        self.assertEqual(Notification.objects.filter(recipient=visitor).count(), 2)

        page = self.client.get(reverse('board-detail', args=[board.id]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Estás en una')

    def test_visitors_are_isolated(self):
        from boards.models import Board

        self._enter_demo()
        first = User.objects.get(is_demo=True, first_name='Invitado')
        other = self.client_class()
        self._enter_demo(other)
        second = User.objects.filter(is_demo=True, first_name='Invitado').exclude(pk=first.pk).get()

        first_board = Board.objects.filter(owner=first).first()
        second_board = Board.objects.filter(owner=second).first()
        self.assertNotEqual(first_board.organization_id, second_board.organization_id)
        resp = other.get(reverse('board-detail', args=[first_board.id]))
        self.assertIn(resp.status_code, (403, 404))

    def test_returning_visitor_reuses_sandbox(self):
        self._enter_demo()
        self.client.post(reverse('logout'))
        self._enter_demo()
        self.assertEqual(User.objects.filter(is_demo=True, first_name='Invitado').count(), 1)

    def test_authenticated_user_is_not_switched_to_demo(self):
        User.objects.create_user(username='real', password='realpass123')
        self.client.login(username='real', password='realpass123')
        resp = self._enter_demo()
        self.assertRedirects(resp, reverse('home'))
        self.assertFalse(User.objects.filter(is_demo=True).exists())

    def test_demo_user_cannot_change_email(self):
        self._enter_demo()
        visitor = User.objects.get(is_demo=True, first_name='Invitado')
        self.client.post(reverse('perfil'), {
            'first_name': 'Hack', 'last_name': '', 'email': 'someone@real.com', 'bio': '',
        })
        visitor.refresh_from_db()
        self.assertEqual(visitor.first_name, 'Hack')
        self.assertEqual(visitor.email, '')

    def test_cleanup_removes_expired_sandboxes_only(self):
        from datetime import timedelta

        from django.utils import timezone

        from boards.demo import cleanup_expired_demos, create_demo_sandbox
        from boards.models import Board
        from organizations.models import Organization

        real = User.objects.create_user(username='real', password='realpass123')
        old_user, old_org, _ = create_demo_sandbox()
        fresh_user, fresh_org, _ = create_demo_sandbox()
        User.objects.filter(username__startswith=old_user.username).update(
            date_joined=timezone.now() - timedelta(hours=25),
        )

        deleted = cleanup_expired_demos()

        self.assertEqual(deleted, 3)  # visitante + 2 compañeros
        self.assertFalse(User.objects.filter(username__startswith=old_user.username).exists())
        self.assertFalse(Organization.objects.filter(pk=old_org.pk).exists())
        self.assertFalse(Board.objects.filter(organization_id=old_org.pk).exists())
        self.assertTrue(User.objects.filter(pk=fresh_user.pk).exists())
        self.assertTrue(Organization.objects.filter(pk=fresh_org.pk).exists())
        self.assertTrue(User.objects.filter(pk=real.pk).exists())

    def test_cleanup_recycles_oldest_over_cap(self):
        from datetime import timedelta

        from boards.demo import cleanup_expired_demos, create_demo_sandbox

        oldest, _, _ = create_demo_sandbox()
        newer, _, _ = create_demo_sandbox()
        User.objects.filter(username__startswith=newer.username).update(
            date_joined=oldest.date_joined + timedelta(seconds=1),
        )

        cleanup_expired_demos(max_active=1)

        self.assertFalse(User.objects.filter(username__startswith=oldest.username).exists())
        self.assertEqual(User.objects.filter(username__startswith=newer.username).count(), 3)

    def test_seed_demo_command_still_works(self):
        from django.core.management import call_command

        from boards.models import Board

        call_command('seed_demo', stdout=StringIO())
        demo = User.objects.get(username='demo')
        self.assertFalse(demo.is_demo)
        self.assertTrue(demo.check_password('demo12345'))
        self.assertEqual(Board.objects.filter(owner=demo).count(), 2)
        self.assertTrue(User.objects.filter(username='ana').exists())
