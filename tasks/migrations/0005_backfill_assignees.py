# Rellena la M2M assignees a partir del antiguo FK assignee (no destructivo).

from django.db import migrations


def backfill_assignees(apps, schema_editor):
    Card = apps.get_model('tasks', 'Card')
    for card in Card.objects.filter(assignee__isnull=False):
        card.assignees.add(card.assignee_id)


def reverse_noop(apps, schema_editor):
    # Irreversible de forma segura: no vaciamos assignees al revertir.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0004_card_assignees_alter_card_assignee_comment_subtask'),
    ]

    operations = [
        migrations.RunPython(backfill_assignees, reverse_noop),
    ]
