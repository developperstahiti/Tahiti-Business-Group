"""
Management command pour lancer les agents de scraping automatique.

Usage:
    python manage.py run_agents            # Scrape + tri automatique
    python manage.py run_agents --dry-run  # Simule sans creer d'articles
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Scrape les sources polynesiennes et trie les articles automatiquement'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Simuler sans creer d'articles")

    def handle(self, *args, **options):
        from rubriques.agents import run_all_agents

        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('Mode DRY RUN - aucun article ne sera cree'))

        self.stdout.write('Scraping + tri automatique en cours...')
        results = run_all_agents(dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS(
            f'  > {results.get("info", 0)} Infos'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  > {results.get("promo", 0)} Promos'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  > {results.get("nouveaute", 0)} Nouveautes'
        ))

        total = sum(results.values())
        self.stdout.write(self.style.SUCCESS(f'\nTotal: {total} articles publies'))
