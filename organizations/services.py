# Lógica reutilizable de organizaciones.

from django.db import transaction

from .models import Organization, OrganizationMembership


def get_or_create_personal_organization(user):
    """Garantiza que el usuario tenga su organización personal + membership owner.

    Se usa en el registro (usuarios nuevos) y en los seeders. La migración de
    datos replica esta lógica para los usuarios ya existentes. Atómico y con
    re-comprobación dentro de la transacción para evitar orgs personales
    duplicadas ante peticiones concurrentes.
    """
    existing = (
        OrganizationMembership.objects
        .filter(user=user, organization__is_personal=True)
        .select_related('organization')
        .first()
    )
    if existing is not None:
        return existing.organization

    with transaction.atomic():
        existing = (
            OrganizationMembership.objects
            .select_for_update()
            .filter(user=user, organization__is_personal=True)
            .select_related('organization')
            .first()
        )
        if existing is not None:
            return existing.organization

        org = Organization.objects.create(
            name=f'{user.username} (Personal)',
            is_personal=True,
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=user,
            role=OrganizationMembership.Role.OWNER,
        )
        return org


def create_team_organization(user, name, brand=Organization.Brand.FLOWLY):
    """Crea un workspace de equipo (no personal) y hace a `user` su OWNER.

    Usado por la creación de workspaces desde la UI. Atómico: la org y la
    membership owner se crean juntas o no se crea ninguna.
    """
    with transaction.atomic():
        org = Organization.objects.create(
            name=name,
            is_personal=False,
            brand=brand,
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=user,
            role=OrganizationMembership.Role.OWNER,
        )
        return org


def join_organization(user, invite):
    """Une a `user` a la organización del invite con el rol del invite.

    Idempotente: si ya es miembro no cambia su rol. Solo afecta a esa
    organización (aislamiento multi-tenant).
    """
    membership, _ = OrganizationMembership.objects.get_or_create(
        organization=invite.organization,
        user=user,
        defaults={'role': invite.role},
    )
    return membership
