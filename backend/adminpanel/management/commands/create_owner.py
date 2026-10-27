"""Securely create (or promote) the platform owner/admin account.

There is deliberately NO admin signup endpoint or public UI. The owner
account is provisioned from the server by a developer/operator:

    python manage.py create_owner --username owner --email owner@example.com

The password is entered interactively (hidden input) unless supplied via
--password for scripted provisioning. The account follows the exact same
Cognito email-confirmation flow as every other InfluenceHub account: it
is created inactive, Cognito emails an OTP, and the owner confirms it via
the standard verify-email step before signing in at /owner/login.
"""

import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from accounts import cognito
from accounts.models import UserRole


class Command(BaseCommand):
    help = "Create or promote the platform owner/admin account (never exposed in public signup)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username for the owner account.")
        parser.add_argument("--email", required=True, help="Email address for the owner account.")
        parser.add_argument(
            "--password",
            help="Initial password. Omit to be prompted securely (input hidden).",
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Additionally grant Django admin-site superuser rights.",
        )

    def handle(self, *args, **options):
        username: str = options["username"].strip()
        email: str = options["email"].strip()
        password: str = options.get("password") or ""
        make_superuser: bool = options["superuser"]

        if "@" not in email:
            raise CommandError("Provide a valid email address.")

        user = User.objects.filter(username__iexact=username).first()
        existing_by_email = User.objects.filter(email__iexact=email).first()
        user = user or existing_by_email

        if user is None:
            if not password:
                password = getpass.getpass("Password for the owner account: ")
                confirm = getpass.getpass("Confirm password: ")
                if password != confirm:
                    raise CommandError("Passwords do not match.")
            if len(password) < 8:
                raise CommandError("Use at least 8 characters for the password.")

            # Inactive until the Cognito-emailed OTP is confirmed, identical
            # to every other signup on the platform.
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False,
            )
            # Cognito owns credentials - PostgreSQL keeps no usable password.
            user.set_unusable_password()
            if make_superuser:
                user.is_superuser = True
                user.is_staff = True
            user.save(update_fields=["password", "is_superuser", "is_staff"])

            cognito.sign_up(email=user.email, password=password, role="owner")
            self.stdout.write(self.style.SUCCESS(
                f"Owner account '{username}' created. A verification code was emailed - "
                "confirm it via the standard verify-email step, then sign in at /owner/login."
            ))
        else:
            self.stdout.write(f"Existing account found: {user.username} ({user.email})")

        role, created = UserRole.objects.get_or_create(user=user, defaults={"role": "owner"})
        if not created and role.role != "owner":
            role.role = "owner"
            role.save(update_fields=["role"])
            self.stdout.write(self.style.SUCCESS(f"Promoted '{user.username}' to the owner role."))
        elif created:
            self.stdout.write(self.style.SUCCESS(f"Assigned the owner role to '{user.username}'."))

        if make_superuser and not user.is_superuser:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
            self.stdout.write(self.style.SUCCESS("Granted Django admin-site superuser rights."))

        self.stdout.write(self.style.SUCCESS("Done. The owner can sign in privately at /owner/login."))
