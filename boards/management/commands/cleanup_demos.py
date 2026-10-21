"""
Borra los sandboxes del acceso demo caducados.

El acceso demo ya limpia de forma perezosa cada vez que crea un sandbox; este
comando sirve para lanzarlo a mano o desde un cron.

Usage:
    python manage.py cleanup_demos
"""

from django.core.management.base import BaseCommand

from boards.demo import cleanup_expired_demos


class Command(BaseCommand):
    help = 'Delete expired demo sandboxes (demo users, their teammates and organizations).'

    def handle(self, *args, **opts):
        deleted = cleanup_expired_demos()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} demo user(s).'))
