# Tests de perfil de usuario (Fase 5) + apariencia y avatar (Refinamientos v2).

import tempfile
from io import BytesIO

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
