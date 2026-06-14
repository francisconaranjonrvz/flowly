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
