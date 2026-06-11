# Modelo de usuario personalizado.

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .validators import validate_avatar_extension, validate_avatar_size

# Umbrales de presencia (segundos desde last_seen).
PRESENCE_ONLINE_SECS = 90
PRESENCE_AWAY_SECS = 300

# Paletas del personaje 8-bit de la Office (índices guardados en el User).
CHAR_SKINS = ['#f4c9a3', '#e0a878', '#c68642', '#8d5524']
CHAR_HAIRS = ['#2b2b2b', '#6b4423', '#caa53d', '#b03a2e', '#7d3cb5', '#d6d6d6']
CHAR_SHIRTS = ['#6366f1', '#a3c93a', '#10b981', '#ef4444', '#f59e0b', '#3b82f6']
CHAR_HAIR_STYLES = ['short', 'long', 'cap', 'bald']


class User(AbstractUser):
    """Usuario con campos extra para el perfil."""

    class ThemeBrand(models.TextChoices):
        FLOWLY = 'flowly', 'Flowly'
        NSW = 'nsw', 'NoSoloWebs'

    class ThemeMode(models.TextChoices):
        LIGHT = 'light', 'Claro'
        DARK = 'dark', 'Oscuro'

    class StatusState(models.TextChoices):
        AVAILABLE = 'available', 'Disponible'
        WORKING = 'working', 'Concentrado'
        BUSY = 'busy', 'Ocupado'
        AWAY = 'away', 'Ausente'

    bio = models.TextField(blank=True)
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        validators=[validate_avatar_extension, validate_avatar_size],
        help_text='Imagen de perfil (PNG, JPG o WEBP, máx. 2 MB).',
    )
    # Preferencias de aspecto (vacío = heredar de la organización / automático).
    theme_brand = models.CharField(
        max_length=20, choices=ThemeBrand.choices, blank=True, default='',
        help_text='Tema visual preferido. Vacío = heredar de la organización.',
    )
    theme_mode = models.CharField(
        max_length=10, choices=ThemeMode.choices, blank=True, default='',
        help_text='Claro u oscuro. Vacío = automático (según sistema/organización).',
    )
    # Presencia / estado (para topbar, equipo y Flowly Office).
    last_seen = models.DateTimeField(null=True, blank=True)
    status_state = models.CharField(
        max_length=10, choices=StatusState.choices, default=StatusState.AVAILABLE,
    )
    status_message = models.CharField(max_length=80, blank=True)
    # Aspecto del personaje 8-bit (índices de paleta; null = auto por id).
    char_skin = models.PositiveSmallIntegerField(null=True, blank=True)
    char_hair = models.PositiveSmallIntegerField(null=True, blank=True)
    char_hair_style = models.PositiveSmallIntegerField(null=True, blank=True)
    char_shirt = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['username']
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.username

    def get_full_name_or_username(self):
        """Devuelve el nombre completo o el username si no tiene."""
        full = super().get_full_name()
        return full if full.strip() else self.username

    @property
    def presence(self):
        """'online' | 'away' | 'offline' a partir de last_seen (heartbeat)."""
        if not self.last_seen:
            return 'offline'
        delta = (timezone.now() - self.last_seen).total_seconds()
        if delta < PRESENCE_ONLINE_SECS:
            return 'online'
        if delta < PRESENCE_AWAY_SECS:
            return 'away'
        return 'offline'

    @property
    def is_online(self):
        return self.presence == 'online'

    @property
    def character(self):
        """Colores/estilo del personaje 8-bit. Si un campo es null, se elige de
        forma determinista por el id (cada usuario tiene un look estable)."""
        base = self.id or 0

        def pick(value, options, salt):
            idx = value if value is not None else (base + salt) % len(options)
            return options[idx % len(options)]

        return {
            'skin': pick(self.char_skin, CHAR_SKINS, 0),
            'hair': pick(self.char_hair, CHAR_HAIRS, 1),
            'shirt': pick(self.char_shirt, CHAR_SHIRTS, 2),
            'hair_style': pick(self.char_hair_style, CHAR_HAIR_STYLES, 3),
        }
