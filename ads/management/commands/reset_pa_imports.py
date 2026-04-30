"""Réinitialise toutes les annonces & comptes importés depuis petites-annonces.pf.

⚠ DESTRUCTIF : supprime toutes les annonces is_imported=True et tous les
comptes is_imported=True. Utiliser uniquement pour repartir de zéro.

Usage :
    python manage.py reset_pa_imports                 # demande confirmation
    python manage.py reset_pa_imports --confirm       # exécute directement
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ads.models import Annonce, PASyncRun

User = get_user_model()


class Command(BaseCommand):
    help = "Supprime toutes les annonces et comptes importés depuis petites-annonces.pf"

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='Confirme la suppression sans demander.')
        parser.add_argument('--keep-runs', action='store_true',
                            help='Ne supprime pas les logs PASyncRun.')

    def handle(self, *args, **opts):
        nb_annonces = Annonce.objects.filter(is_imported=True).count()
        nb_users    = User.objects.filter(is_imported=True).count()
        nb_runs     = PASyncRun.objects.count()

        self.stdout.write(self.style.WARNING(
            f'À supprimer : {nb_annonces} annonces · {nb_users} comptes · '
            f'{nb_runs} runs PASyncRun{" (conservés)" if opts["keep_runs"] else ""}'
        ))

        if not opts['confirm']:
            ans = input('Tape OUI pour confirmer : ')
            if ans.strip() != 'OUI':
                self.stdout.write(self.style.ERROR('Annulé.'))
                return

        # Ordre : annonces → comptes (CASCADE OK car users.delete() supprime aussi
        # les annonces dont ils sont propriétaires, mais on a déjà filtré is_imported)
        deleted_annonces = Annonce.objects.filter(is_imported=True).delete()
        deleted_users    = User.objects.filter(is_imported=True).delete()
        if not opts['keep_runs']:
            PASyncRun.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'Nettoyage OK : {deleted_annonces[0]} annonces, {deleted_users[0]} comptes supprimés.'
        ))
