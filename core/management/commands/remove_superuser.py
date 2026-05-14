"""
Demotes a superuser to a regular staff user by clearing is_superuser.

Usage:
  python manage.py remove_superuser
  python manage.py remove_superuser --username someuser
  python manage.py remove_superuser --username someuser --remove-staff
"""

import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Remove superuser status from a user (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default=None,
            help='Username to demote (default: DJANGO_SUPERUSER_USERNAME env var, then "admin")',
        )
        parser.add_argument(
            '--remove-staff',
            action='store_true',
            help='Also clear is_staff (makes the user a plain volunteer)',
        )

    def handle(self, *args, **options):
        username = options['username'] or os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        if not user.is_superuser:
            self.stdout.write(f"User '{username}' is not a superuser — nothing to do.")
            return

        user.is_superuser = False
        if options['remove_staff']:
            user.is_staff = False
        user.save(update_fields=['is_superuser', 'is_staff'] if options['remove_staff'] else ['is_superuser'])

        if options['remove_staff']:
            self.stdout.write(self.style.SUCCESS(
                f"User '{username}' superuser and staff status removed."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"User '{username}' superuser status removed (still staff)."
            ))
