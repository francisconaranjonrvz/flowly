# Modelos de organización (tenant), membresía y tema de marca.

import secrets

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify


def _generate_invite_token():
    return secrets.token_urlsafe(32)

hex_color_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{6})$',
    message='Usa un color hexadecimal con el formato #RRGGBB.',
)


class Organization(models.Model):
    """Tenant: agrupa tableros, miembros y un tema de marca."""

    class Brand(models.TextChoices):
        FLOWLY = 'flowly', 'Flowly'
        NSW = 'nsw', 'NoSoloWebs'

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_personal = models.BooleanField(default=False)
    brand = models.CharField(
        max_length=20, choices=Brand.choices, default=Brand.FLOWLY,
        help_text='Marca/tema visual (define data-brand en el front).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'organization'
        verbose_name_plural = 'organizations'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def _build_unique_slug(self):
        base = slugify(self.name) or 'org'
        slug = base
        counter = 2
        while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{counter}'
            counter += 1
        return slug


class OrganizationMembership(models.Model):
    """Relación usuario-organización con rol a nivel de tenant."""

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
        VIEWER = 'viewer', 'Viewer'

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['organization', 'user']
        verbose_name = 'organization membership'
        verbose_name_plural = 'organization memberships'

    def __str__(self):
        return f'{self.user} → {self.organization} ({self.role})'

    @property
    def is_manager(self):
        return self.role in (self.Role.OWNER, self.Role.ADMIN)


class OrganizationInvite(models.Model):
    """Enlace de invitación a un workspace (un enlace activo por organización).

    Quien abre el enlace y confirma se une a la organización con el rol del
    invite. Regenerar el token invalida el anterior. Sin email: la única
    barrera es conocer el token (suficiente para un MVP de equipo).
    """

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='invite',
    )
    token = models.CharField(
        max_length=64, unique=True, default=_generate_invite_token,
    )
    role = models.CharField(
        max_length=10,
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.MEMBER,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_invites',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'organization invite'
        verbose_name_plural = 'organization invites'

    def __str__(self):
        return f'Invite de {self.organization}'

    def regenerate(self):
        self.token = _generate_invite_token()
        self.save(update_fields=['token'])


def _hex_field(help_text=''):
    return models.CharField(
        max_length=7, blank=True, validators=[hex_color_validator], help_text=help_text,
    )


class OrganizationTheme(models.Model):
    """Tema de marca de una organización: sobrescribe primitivos en runtime.

    Todos los colores son opcionales (vacío = valor por defecto de Flowly), así
    que una organización puede personalizar desde solo el acento hasta la paleta
    completa (fondos, textos, bordes) para un aspecto totalmente distinto.
    """

    class Mode(models.TextChoices):
        DARK = 'dark', 'Oscuro'
        LIGHT = 'light', 'Claro'
        AUTO = 'auto', 'Automático'

    class OnAccent(models.TextChoices):
        AUTO = 'auto', 'Automático (contraste)'
        LIGHT = 'light', 'Texto claro'
        DARK = 'dark', 'Texto oscuro'

    class Font(models.TextChoices):
        DEFAULT = '', 'Por defecto (Flowly)'
        SPACE_GROTESK = 'spacegrotesk', 'Space Grotesk'
        MULISH = 'mulish', 'Mulish'
        INTER = 'inter', 'Inter'
        IBM_PLEX = 'ibmplexsans', 'IBM Plex Sans'
        GOSHA = 'ppgoshasans', 'PP Gosha Sans'

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='theme',
    )

    # Acento
    brand_accent = _hex_field('Acento #RRGGBB. Vacío = indigo de Flowly.')
    brand_accent_hover = _hex_field('Acento al pasar el ratón. Vacío = igual que el acento.')
    on_accent_mode = models.CharField(
        max_length=10, choices=OnAccent.choices, default=OnAccent.AUTO,
        help_text='Color del texto sobre el acento. Automático elige por contraste.',
    )

    # Superficies (fondos)
    brand_bg_primary = _hex_field('Fondo principal (página).')
    brand_bg_secondary = _hex_field('Fondo de superficies (columnas/tarjetas).')
    brand_bg_tertiary = _hex_field()
    brand_bg_hover = _hex_field()
    brand_bg_active = _hex_field()
    brand_bg_elevated = _hex_field()

    # Texto
    brand_text_primary = _hex_field('Texto principal.')
    brand_text_secondary = _hex_field()
    brand_text_tertiary = _hex_field()

    # Bordes / scrollbar (canal de superposición; en tema claro, una tinta oscura)
    brand_overlay = _hex_field('Color base de bordes/scrollbar.')

    # Estados (opcional)
    brand_success = _hex_field()
    brand_warning = _hex_field()

    # Tipografía
    font_display = models.CharField(
        max_length=20, choices=Font.choices, blank=True, default='',
        help_text='Fuente de titulares/UI.',
    )
    font_body = models.CharField(
        max_length=20, choices=Font.choices, blank=True, default='',
        help_text='Fuente del cuerpo de texto.',
    )

    # Modo por defecto
    theme_mode = models.CharField(
        max_length=10, choices=Mode.choices, default=Mode.DARK,
        help_text='Modo por defecto de la organización (el usuario puede cambiarlo).',
    )

    class Meta:
        verbose_name = 'organization theme'
        verbose_name_plural = 'organization themes'

    def __str__(self):
        return f'Tema de {self.organization}'

    def save(self, *args, **kwargs):
        # Defensa en profundidad: nunca persistir un hex inválido, venga del
        # admin, un seeder o el shell.
        self.full_clean(exclude=['organization'])
        super().save(*args, **kwargs)
