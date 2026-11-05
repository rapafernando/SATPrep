import os

from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Create the first admin from DJANGO_SUPERUSER_* variables if it does not exist yet."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("An admin account already exists; leaving it alone.")
            return
        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "No admin yet and DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD are not set. "
                    "Create one with: docker compose exec web python manage.py createsuperuser"
                )
            )
            return
        user = User.objects.create_superuser(username=username, email=email, password=password)
        user.display_name = "Admin"
        user.ad_free = True  # the admin does not need to see their own ads
        user.save(update_fields=["display_name", "ad_free", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Created admin account '{username}'."))
