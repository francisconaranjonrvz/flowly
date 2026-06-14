"""Siembra la organización NoSoloWebs (primer tenant) con su tema de marca
y un tablero de ejemplo, para poder ver el theming por organización en vivo.

Uso:
    python manage.py seed_nosolowebs
    python manage.py seed_nosolowebs --member demo
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from boards.models import Board, Column
from organizations.models import Organization, OrganizationMembership, OrganizationTheme
from tasks.models import Card

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea la organización NoSoloWebs (primer tenant) con su tema lime/negro.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--member', default='demo',
            help='Usuario a añadir como admin de NoSoloWebs (default: demo).',
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        org, _ = Organization.objects.get_or_create(
            slug='nosolowebs', defaults={'name': 'NoSoloWebs'},
        )
        if org.brand != Organization.Brand.NSW:
            org.brand = Organization.Brand.NSW
            org.save(update_fields=['brand'])

        theme, _ = OrganizationTheme.objects.get_or_create(organization=org)
        # Acento lima sobre tema CLARO (look NSW completamente distinto al de Flowly).
        theme.brand_accent = '#D6FF00'        # NSW amarillo lima
        theme.brand_accent_hover = '#BFE600'
        theme.on_accent_mode = OrganizationTheme.OnAccent.AUTO  # lima -> texto negro
        # Superficies claras
        theme.brand_bg_primary = '#EAEAEA'    # gris 1 (página)
        theme.brand_bg_secondary = '#FFFFFF'  # columnas / tarjetas
        theme.brand_bg_tertiary = '#F4F4F4'
        theme.brand_bg_hover = '#E4E4E4'
        theme.brand_bg_active = '#DADADA'
        theme.brand_bg_elevated = '#FFFFFF'
        # Texto oscuro
        theme.brand_text_primary = '#1D1D1D'  # negro NSW
        theme.brand_text_secondary = '#5A5A5A'
        theme.brand_text_tertiary = '#9C9C9C'  # gris 2
        # Bordes/scrollbar como tinta oscura sobre claro
        theme.brand_overlay = '#1D1D1D'
        # Estados con la paleta NSW
        theme.brand_success = '#5CE9C3'       # verdiazul
        theme.brand_warning = '#CE9B59'       # naranjiamarillo
        # Tipografía NSW
        theme.font_display = OrganizationTheme.Font.SPACE_GROTESK
        theme.font_body = OrganizationTheme.Font.MULISH
        theme.theme_mode = OrganizationTheme.Mode.DARK  # NSW por defecto en oscuro
        theme.full_clean(exclude=['organization'])
        theme.save()

        user = None
        member = opts['member']
        try:
            user = User.objects.get(username=member)
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f"Usuario '{member}' no existe; organización creada sin miembro ni tablero.",
            ))
        else:
            OrganizationMembership.objects.get_or_create(
                organization=org, user=user,
                defaults={'role': OrganizationMembership.Role.ADMIN},
            )
            self.stdout.write(self.style.SUCCESS(f"'{member}' añadido como admin de NoSoloWebs."))

        if user is not None and not org.boards.exists():
            self._sample_board(org, user)

        self.stdout.write(self.style.SUCCESS(
            'NoSoloWebs sembrada (marca NSW, oscuro por defecto, lima #D6FF00 + Space Grotesk/Mulish).',
        ))

    def _sample_board(self, org, user):
        board = Board.objects.create(
            owner=user, organization=org,
            name='Web NoSoloWebs',
            description='Tablero de marca del primer tenant.',
        )
        cols = {}
        for i, title in enumerate(['Backlog', 'En curso', 'Hecho']):
            cols[title] = Column.objects.create(board=board, title=title, order=i)
        Card.objects.create(column=cols['Backlog'], title='Rediseño de la home', priority=3, order=0)
        Card.objects.create(column=cols['Backlog'], title='Sección de servicios', priority=2, order=1)
        Card.objects.create(column=cols['En curso'], title='Integrar identidad lime', priority=2, order=0)
        Card.objects.create(column=cols['Hecho'], title='Logotipo e isotipo', priority=1, order=0)
