from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Envoie un email de test pour vérifier la configuration SMTP Brevo'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Adresse email destinataire')

    def handle(self, *args, **options):
        recipient = options['email']
        self.stdout.write(f'Envoi d\'un email de test à {recipient}...')
        self.stdout.write(f'SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'User: {settings.EMAIL_HOST_USER}')
        try:
            send_mail(
                subject='Test email — Tahiti Business Group',
                message=(
                    'Cet email confirme que la configuration SMTP '
                    'de Tahiti Business Group fonctionne correctement.\n\n'
                    '— TBG'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Email envoyé avec succès à {recipient} !'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur : {e}'))
