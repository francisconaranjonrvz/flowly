"""
Demo seeder.

Creates a demo user, two boards with realistic columns/labels/cards, and
hands you ready-to-use credentials to log in. Idempotent: re-running
deletes the demo user's data and starts over.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --user demo --password demo12345 --reset
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from boards.demo import DEMO_BOARDS, seed_demo_workspace
from collab.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with a demo user and two example boards.'

    def add_arguments(self, parser):
        parser.add_argument('--user', default='demo', help='Demo username (default: demo).')
        parser.add_argument('--password', default='demo12345', help='Demo password (default: demo12345).')
        parser.add_argument('--reset', action='store_true', help='Wipe the demo user\'s boards before seeding.')

    @transaction.atomic
    def handle(self, *args, **opts):
        username = opts['user']
        password = opts['password']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'},
        )
        if created or opts['reset']:
            user.set_password(password)
            user.save()

        if opts['reset']:
            user.owned_boards.all().delete()
            Notification.objects.filter(recipient=user).delete()
            self.stdout.write(self.style.WARNING(f'Wiped existing boards owned by {username}.'))

        seed_demo_workspace(user)

        self.stdout.write(self.style.SUCCESS('\nDemo seeded.'))
        self.stdout.write(f'  user:     {username}')
        self.stdout.write(f'  password: {password}')
        self.stdout.write(f'  boards:   {len(DEMO_BOARDS)}\n')
