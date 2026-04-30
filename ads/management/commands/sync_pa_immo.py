"""Synchronise les annonces immobilier de petites-annonces.pf vers TBG.

Usage :
    python manage.py sync_pa_immo                  # Sync complet immobilier
    python manage.py sync_pa_immo --dry-run        # Test sans écrire en DB
    python manage.py sync_pa_immo --limit 10       # Max 10 annonces par sous-cat
    python manage.py sync_pa_immo --cat 3          # Uniquement c=3 (Vends terrain)
    python manage.py sync_pa_immo --no-photos      # Ne télécharge pas les photos
"""
from django.core.management.base import BaseCommand

from ads.scrapers.sync import sync_immobilier


class Command(BaseCommand):
    help = 'Synchronise les annonces immobilier de petites-annonces.pf vers TBG'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Mode test : n'écrit rien en base.",
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help="Max d'annonces traitées par sous-catégorie.",
        )
        parser.add_argument(
            '--cat', type=int, default=None,
            choices=[1, 2, 3, 4, 5, 6],
            help="Catégorie PA spécifique (1=apparts vente, 2=maisons vente, "
                 "3=terrains, 4=apparts loc, 5=maisons loc, 6=saisonnières)",
        )
        parser.add_argument(
            '--no-photos', action='store_true',
            help="Ne télécharge pas les photos (plus rapide pour tests).",
        )

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        if dry:
            self.stdout.write(self.style.WARNING('[DRY RUN] Aucune écriture en DB'))

        stats = sync_immobilier(
            limit=opts['limit'],
            dry_run=dry,
            skip_photos=opts['no_photos'],
            only_cat=opts['cat'],
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═════ Sync terminé ═════'))
        self.stdout.write(f'  Créés      : {stats["created"]}')
        self.stdout.write(f'  Mis à jour : {stats["updated"]}')
        self.stdout.write(f'  Archivés   : {stats["archived"]}')
        self.stdout.write(f'  Skip       : {stats["skipped"]}')
        self.stdout.write(f'  Photos DL  : {stats["photos_downloaded"]}')
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f'  Erreurs   : {stats["errors"]}'))
