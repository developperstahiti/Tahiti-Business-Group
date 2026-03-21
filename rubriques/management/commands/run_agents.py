"""
Management command pour lancer les agents de scraping automatique.

Usage:
    python manage.py run_agents              # Lance les 3 agents
    python manage.py run_agents --info       # Lance seulement l'agent Info
    python manage.py run_agents --promo      # Lance seulement l'agent Promo
    python manage.py run_agents --nouveaute  # Lance seulement l'agent Nouveauté
    python manage.py run_agents --dry-run    # Simule sans créer d'articles
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Lance les agents de scraping automatique pour les rubriques TBG'

    def add_arguments(self, parser):
        parser.add_argument('--info', action='store_true', help='Lancer uniquement l\'agent Info')
        parser.add_argument('--promo', action='store_true', help='Lancer uniquement l\'agent Promo')
        parser.add_argument('--nouveaute', action='store_true', help='Lancer uniquement l\'agent Nouveauté')
        parser.add_argument('--dry-run', action='store_true', help='Simuler sans créer d\'articles')

    def handle(self, *args, **options):
        from rubriques.agents import run_info_agent, run_promo_agent, run_nouveaute_agent

        dry_run = options['dry_run']
        specific = options['info'] or options['promo'] or options['nouveaute']

        if dry_run:
            self.stdout.write(self.style.WARNING('Mode DRY RUN - aucun article ne sera cree'))

        results = {}

        if not specific or options['info']:
            self.stdout.write('Lancement agent Info...')
            results['info'] = run_info_agent(dry_run=dry_run)
            self.stdout.write(self.style.SUCCESS(f'  > {results["info"]} articles Info crees'))

        if not specific or options['promo']:
            self.stdout.write('Lancement agent Promo...')
            results['promo'] = run_promo_agent(dry_run=dry_run)
            self.stdout.write(self.style.SUCCESS(f'  > {results["promo"]} articles Promo crees'))

        if not specific or options['nouveaute']:
            self.stdout.write('Lancement agent Nouveaute...')
            results['nouveaute'] = run_nouveaute_agent(dry_run=dry_run)
            self.stdout.write(self.style.SUCCESS(f'  > {results["nouveaute"]} articles Nouveaute crees'))

        total = sum(results.values())
        self.stdout.write(self.style.SUCCESS(f'\nTotal: {total} articles publies'))
