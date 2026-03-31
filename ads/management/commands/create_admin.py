import os
from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = "Cree ou reset le compte admin + s'assure que le compte principal est admin"

    def handle(self, *args, **options):
        # Compte admin par défaut
        email = "admin@tahitibusinessgroup.com"
        password = os.environ.get('ADMIN_PASSWORD', 'TBG-Admin-2026!Secure')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "nom": "Admin TBG",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
        else:
            # Mise à jour des permissions uniquement, sans toucher au mot de passe
            User.objects.filter(email=email).update(
                is_staff=True,
                is_superuser=True,
                role="admin",
            )

        status = "cree" if created else "mis a jour (mdp inchange)"
        self.stdout.write(self.style.SUCCESS(
            f"Admin {email} {status} avec succes."
        ))

        # S'assurer que le compte principal est toujours admin
        try:
            owner = User.objects.get(email="mathyscocogames@gmail.com")
            if not owner.is_staff or not owner.is_superuser:
                owner.is_staff = True
                owner.is_superuser = True
                owner.save(update_fields=['is_staff', 'is_superuser'])
                self.stdout.write(self.style.SUCCESS(
                    "mathyscocogames@gmail.com promu admin."
                ))
        except User.DoesNotExist:
            pass
