from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Promote un utilisateur en superadmin (is_staff + is_superuser)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email de l\'utilisateur à promouvoir')

    def handle(self, *args, **options):
        email = options['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Aucun utilisateur avec l\'email {email}'))
            return

        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(update_fields=['is_staff', 'is_superuser', 'is_active'])
        self.stdout.write(self.style.SUCCESS(
            f'Utilisateur {email} promu superadmin avec succès.'
        ))
