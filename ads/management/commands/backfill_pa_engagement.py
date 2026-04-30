"""Applique des stats d'engagement aléatoires aux annonces importées existantes.

Pour les annonces qui ont été importées AVANT l'ajout du système de fake stats
(views/clics/saves restés à 0). À utiliser une seule fois après déploiement.

Usage :
    python manage.py backfill_pa_engagement              # toutes les annonces is_imported avec views=0
    python manage.py backfill_pa_engagement --force      # toutes les annonces is_imported (override existant)
    python manage.py backfill_pa_engagement --dry-run    # affiche sans modifier
"""
import random

from django.core.management.base import BaseCommand

from ads.models import Annonce
from ads.scrapers.sync import _generate_fake_engagement


class Command(BaseCommand):
    help = "Applique des stats d'engagement aléatoires aux annonces importées"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Régénère même si views > 0.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Affiche les changements sans modifier la DB.')

    def handle(self, *args, **opts):
        qs = Annonce.objects.filter(is_imported=True)
        if not opts['force']:
            qs = qs.filter(views=0)

        total = qs.count()
        self.stdout.write(f'Annonces importées à backfiller : {total}')

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('[DRY RUN] Aucune écriture en DB'))
            return

        for ann in qs:
            views, clics, saves = _generate_fake_engagement()
            ann.views = views
            ann.clics = clics
            ann.fake_saves_count = saves
            ann.save(update_fields=['views', 'clics', 'fake_saves_count'])

        self.stdout.write(self.style.SUCCESS(f'OK : {total} annonces mises à jour avec stats aléatoires.'))
