"""
Corrige les localisations des annonces existantes :
1. Peuple le champ 'commune' a partir de 'localisation' pour les annonces ou commune est vide
2. Normalise les noms (Faaa -> Faa'a, etc.)
"""
from django.core.management.base import BaseCommand
from ads.models import Annonce
from ads.localites_polynesie import get_all_communes


# Mapping de correction : termes courants ou mal orthographies -> commune officielle
CORRECTIONS = {
    'faaa': "Faa'a",
    "faa'a": "Faa'a",
    'faa a': "Faa'a",
    'papeete': 'Papeete',
    'pirae': 'Pirae',
    'arue': 'Arue',
    'mahina': 'Mahina',
    'punaauia': 'Punaauia',
    'paea': 'Paea',
    'papara': 'Papara',
    'moorea': 'Moorea-Maiao',
    'taravao': 'Taiarapu-Est',
    'plateau de taravao': 'Taiarapu-Est',
    'teahupoo': 'Taiarapu-Ouest',
    'tautira': 'Taiarapu-Est',
    'mataiea': 'Mataiea',
    'papeari': 'Papeari',
    'uturoa': 'Uturoa',
    'bora bora': 'Bora-Bora',
    'bora-bora': 'Bora-Bora',
    'rangiroa': 'Rangiroa',
    'fakarava': 'Fakarava',
    'tikehau': 'Tikehau',
    'huahine': 'Fare',
    'raiatea': 'Uturoa',
    'nuku hiva': 'Taiohae',
    'hiva oa': 'Atuona',
    'rurutu': 'Rurutu',
    'tubuai': 'Tubuai',
}


class Command(BaseCommand):
    help = 'Corrige et normalise les localisations des annonces'

    def handle(self, *args, **options):
        communes_valides = {c.lower(): c for c in get_all_communes()}
        updated = 0

        for annonce in Annonce.objects.all():
            changed = False
            loc = (annonce.localisation or '').strip()
            loc_lower = loc.lower()

            # Si commune est deja remplie, on passe
            if annonce.commune:
                continue

            # Chercher dans les corrections
            if loc_lower in CORRECTIONS:
                annonce.commune = CORRECTIONS[loc_lower]
                annonce.localisation = annonce.commune
                changed = True
            # Chercher dans les communes valides
            elif loc_lower in communes_valides:
                annonce.commune = communes_valides[loc_lower]
                annonce.localisation = annonce.commune
                changed = True
            # Sinon garder tel quel dans localisation
            else:
                annonce.commune = loc
                changed = True

            if changed:
                annonce.save(update_fields=['commune', 'localisation'])
                updated += 1
                self.stdout.write(f'  {annonce.pk}: "{loc}" > commune="{annonce.commune}"')

        self.stdout.write(self.style.SUCCESS(f'\n{updated} annonces corrigees.'))
