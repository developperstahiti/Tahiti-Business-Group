from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = "Cree ou reset le compte admin"

    def handle(self, *args, **options):
        email = "admin@tahitibusinessgroup.com"
        password = "TBG-Admin-2026!Secure"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "nom": "Admin TBG",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if not created:
            user.is_staff = True
            user.is_superuser = True
            user.role = "admin"

        user.set_password(password)
        user.save()

        status = "cree" if created else "reset"
        self.stdout.write(self.style.SUCCESS(
            f"Admin {email} {status} avec succes."
        ))
