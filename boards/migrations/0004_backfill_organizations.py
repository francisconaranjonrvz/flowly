"""Crea una organización personal por usuario y asigna cada tablero a ella.

Idempotente y reversible. No modifica filas de Column/Label/Card.
"""

from django.db import migrations
from django.utils.text import slugify


def backfill(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Organization = apps.get_model('organizations', 'Organization')
    OrganizationMembership = apps.get_model('organizations', 'OrganizationMembership')
    Board = apps.get_model('boards', 'Board')

    def unique_slug(base):
        base = slugify(base) or 'org'
        slug, counter = base, 2
        while Organization.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    personal_by_user = {}
    for user in User.objects.all():
        existing = (
            OrganizationMembership.objects
            .filter(user=user, organization__is_personal=True)
            .select_related('organization')
            .first()
        )
        if existing is not None:
            personal_by_user[user.id] = existing.organization
            continue
        org = Organization.objects.create(
            name=f'{user.username} (Personal)',
            slug=unique_slug(f'{user.username}-personal'),
            is_personal=True,
        )
        OrganizationMembership.objects.create(
            organization=org, user=user, role='owner',
        )
        personal_by_user[user.id] = org

    for board in Board.objects.filter(organization__isnull=True):
        org = personal_by_user.get(board.owner_id)
        if org is not None:
            board.organization = org
            board.save(update_fields=['organization'])


def reverse(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    Board = apps.get_model('boards', 'Board')
    # Soltar los tableros de sus orgs personales antes de borrarlas (CASCADE).
    Board.objects.filter(organization__is_personal=True).update(organization=None)
    Organization.objects.filter(is_personal=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0003_board_organization'),
        ('organizations', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse),
    ]
