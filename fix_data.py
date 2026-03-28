"""
Script de correction de données — à exécuter via :
    python manage.py shell < fix_data.py

Partie 1 : Corrige le badge Vente/Location sur les annonces immobilières
           dont le type_transaction ne correspond pas au contenu du titre/description.

Partie 2 : Corrige la commune/localisation des annonces qui affichent "Papeete"
           alors que le titre ou la description mentionne une autre commune.
"""

from ads.models import Annonce

# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 1 — Correction badge Vente / Location
# ─────────────────────────────────────────────────────────────────────────────

LOCATION_KEYWORDS = [
    'LOUE', 'LOUER', 'LOCATION', 'À LOUER', 'A LOUER',
    'SAISONNI', 'VACANCES', 'MENSUEL', 'MOIS'
]

VENTE_KEYWORDS = [
    'VENTE', 'VENDRE', 'À VENDRE', 'A VENDRE', 'CESSION'
]

annonces_immo = Annonce.objects.filter(categorie='immobilier')
fixed_location = 0
fixed_vente = 0

for annonce in annonces_immo:
    titre_upper = annonce.titre.upper()
    desc_upper = (annonce.description or '').upper()

    is_location = any(kw in titre_upper or kw in desc_upper for kw in LOCATION_KEYWORDS)
    is_vente = any(kw in titre_upper or kw in desc_upper for kw in VENTE_KEYWORDS)

    if is_location and not is_vente:
        if annonce.type_transaction != 'location':
            annonce.type_transaction = 'location'
            annonce.save(update_fields=['type_transaction'])
            fixed_location += 1
    elif is_vente and not is_location:
        if annonce.type_transaction != 'vente':
            annonce.type_transaction = 'vente'
            annonce.save(update_fields=['type_transaction'])
            fixed_vente += 1

print(f"Badges corrigés : {fixed_location} → location, {fixed_vente} → vente")

# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 2 — Correction localisations (commune affichée comme Papeete à tort)
# ─────────────────────────────────────────────────────────────────────────────

COMMUNE_FIXES = {
    'PIRAE': 'Pirae',
    "FAA'A": "Faa'a",
    'FAAA': "Faa'a",
    'PUNAAUIA': 'Punaauia',
    'PAMATAI': "Faa'a",
    'ARUE': 'Arue',
    'MAHINA': 'Mahina',
    'PAEA': 'Paea',
    'PAPARA': 'Papara',
    'TARAVAO': 'Taiarapu-Est',
    'MOOREA': 'Afareaitu',
}

fixed_loc = 0
for annonce in Annonce.objects.all():
    titre_upper = annonce.titre.upper()
    desc_upper = (annonce.description or '').upper()
    text = titre_upper + ' ' + desc_upper

    current_commune = annonce.commune or annonce.localisation

    for keyword, correct_commune in COMMUNE_FIXES.items():
        if keyword in text and current_commune in ('Papeete', '', None):
            annonce.commune = correct_commune
            annonce.localisation = correct_commune
            annonce.save(update_fields=['commune', 'localisation'])
            fixed_loc += 1
            break

print(f"Localisations corrigées : {fixed_loc}")
