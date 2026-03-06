"""python manage.py clear_demo_data — supprime les utilisateurs @demo.pf et leurs annonces."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Supprime les comptes @demo.pf et leurs annonces (sans recréation)'

    def handle(self, *args, **options):
        User = get_user_model()
        count = User.objects.filter(email__endswith='@demo.pf').count()
        if count:
            User.objects.filter(email__endswith='@demo.pf').delete()
            self.stdout.write(self.style.SUCCESS(
                f'[OK] {count} utilisateurs @demo.pf supprimés (annonces supprimées en cascade).'
            ))
        else:
            self.stdout.write('Aucun utilisateur @demo.pf trouvé.')
