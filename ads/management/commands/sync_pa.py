"""Synchronise les annonces de petites-annonces.pf vers TBG (toutes rubriques).

Usage :
    python manage.py sync_pa                          # toutes rubriques
    python manage.py sync_pa --rubrique immobilier    # uniquement immo
    python manage.py sync_pa --rubrique vehicules     # uniquement véhicules
    python manage.py sync_pa --rubrique occasion      # uniquement occasion
    python manage.py sync_pa --rubrique emploi        # uniquement emploi
    python manage.py sync_pa --rubrique services      # uniquement services
    python manage.py sync_pa --cat 9                  # une seule catégorie PA
    python manage.py sync_pa --dry-run --limit 5      # test sans écriture
    python manage.py sync_pa --no-photos              # sync rapide sans photos
"""
from django.core.management.base import BaseCommand

from ads.scrapers.sync import sync_pa


RUBRIQUES = ['all', 'immobilier', 'vehicules', 'occasion', 'emploi', 'services']


class Command(BaseCommand):
    help = 'Synchronise les annonces de petites-annonces.pf vers TBG'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Mode test : n'écrit rien en base.")
        parser.add_argument('--limit', type=int, default=None,
                            help="Max d'annonces traitées par sous-catégorie.")
        parser.add_argument('--rubrique', type=str, default=None, choices=RUBRIQUES,
                            help="Rubrique TBG à synchroniser (défaut : toutes).")
        parser.add_argument('--cat', type=int, default=None,
                            help="ID PA d'une catégorie spécifique (override rubrique).")
        parser.add_argument('--no-photos', action='store_true',
                            help="Ne télécharge pas les photos.")

    def handle(self, *args, **opts):
        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('[DRY RUN] Aucune écriture en DB'))

        target = opts['rubrique'] or 'toutes rubriques'
        cat_suffix = f' (cat={opts["cat"]})' if opts['cat'] else ''
        self.stdout.write(f'Sync : {target}{cat_suffix}')

        stats = sync_pa(
            limit=opts['limit'],
            dry_run=opts['dry_run'],
            skip_photos=opts['no_photos'],
            only_cat=opts['cat'],
            rubrique=opts['rubrique'],
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═════ Sync terminée ═════'))
        self.stdout.write(f'  Créés          : {stats["created"]}')
        self.stdout.write(f'  Mis à jour     : {stats["updated"]}')
        self.stdout.write(f'  Archivés       : {stats["archived"]}')
        self.stdout.write(f'  Skip           : {stats["skipped"]}')
        self.stdout.write(f'  Photos DL      : {stats["photos_downloaded"]}')
        self.stdout.write(f'  Comptes créés  : {stats.get("users_created", 0)}')
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f'  Erreurs        : {stats["errors"]}'))
