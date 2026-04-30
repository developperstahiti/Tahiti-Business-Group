"""Table de correspondance entre les catégories de petites-annonces.pf et TBG.

Source PA : https://www.petites-annonces.pf/rss.php?c=N
Cible TBG : (categorie, sous_categorie, type_transaction)

c_id PA inventoriés depuis annonces.php?r=N puis fetchage de la home.
Catégories ignorées : Recherche..., Autres trop génériques.
"""

# c_id PA → (categorie_tbg, sous_categorie_tbg, type_transaction_tbg)
PA_TO_TBG = {
    # ─── IMMOBILIER (r=1) ────────────────────────────────────────
    1:  ('immobilier', 'immo-appartements', 'vente'),     # Vends appartement
    2:  ('immobilier', 'immo-maisons',      'vente'),     # Vends maison
    3:  ('immobilier', 'immo-terrains',     'vente'),     # Vends terrain
    4:  ('immobilier', 'immo-appartements', 'location'),  # Loue appartement
    5:  ('immobilier', 'immo-maisons',      'location'),  # Loue maison
    6:  ('immobilier', 'immo-saisonnieres', 'location'),  # Saisonnière

    # ─── VÉHICULES (r=2) ─────────────────────────────────────────
    9:  ('vehicules',  'vehicules-voitures',  'vente'),     # Vends voiture
    10: ('vehicules',  'vehicules-2roues',    'vente'),     # Vends 2 roues
    11: ('vehicules',  'vehicules-bateaux',   'vente'),     # Vends bateau
    12: ('vehicules',  'vehicules-pieces',    'non_applicable'),  # Equipement, pièces
    13: ('vehicules',  'vehicules-pieces',    'non_applicable'),  # Autres
    58: ('vehicules',  'vehicules-voitures',  'location'),  # Loue voiture
    59: ('vehicules',  'vehicules-2roues',    'location'),  # Loue 2 roues
    60: ('vehicules',  'vehicules-bateaux',   'location'),  # Loue bateau

    # ─── BONNES AFFAIRES (r=3) → OCCASION ────────────────────────
    15: ('occasion',   'occasion-meubles',        'non_applicable'),  # Meubles & électroménager
    16: ('occasion',   'occasion-divers',         'non_applicable'),  # Bricolage, jardinage
    17: ('occasion',   'occasion-informatique',   'non_applicable'),  # Informatique
    18: ('occasion',   'occasion-jouets',         'non_applicable'),  # Jeux et jouets
    19: ('occasion',   'occasion-tv',             'non_applicable'),  # TV, Hi-Fi, Vidéo
    20: ('occasion',   'occasion-telephones',     'non_applicable'),  # Téléphonie
    21: ('occasion',   'occasion-sport',          'non_applicable'),  # Articles sport
    22: ('occasion',   'occasion-divers',         'non_applicable'),  # CD, DVD, livres
    23: ('occasion',   'occasion-vetements',      'non_applicable'),  # Vêtements
    24: ('occasion',   'occasion-vetements',      'non_applicable'),  # Bijoux, montres
    25: ('occasion',   'occasion-divers',         'non_applicable'),  # Collections
    26: ('occasion',   'occasion-divers',         'non_applicable'),  # Autres
    33: ('occasion',   'occasion-divers',         'non_applicable'),  # Articles de luxe
    51: ('occasion',   'occasion-puericulture',   'non_applicable'),  # Puériculture
    52: ('occasion',   'occasion-divers',         'non_applicable'),  # Alimentaire
    53: ('occasion',   'occasion-meubles',        'non_applicable'),  # Décoration
    54: ('occasion',   'occasion-divers',         'non_applicable'),  # Fruits & légumes

    # ─── EMPLOI (r=4) ────────────────────────────────────────────
    28: ('emploi',     'emploi-offre',     'non_applicable'),  # Offres
    29: ('emploi',     'emploi-recherche', 'non_applicable'),  # Demandes
    30: ('emploi',     'emploi-offre',     'non_applicable'),  # Formation

    # ─── SERVICES (r=5) ──────────────────────────────────────────
    32: ('services',   'services-cours',     'non_applicable'),  # Cours & leçons
    34: ('services',   'services-autres',    'non_applicable'),  # Excursions
    36: ('services',   'services-autres',    'non_applicable'),  # Prestataires divers
    37: ('services',   'services-autres',    'non_applicable'),  # Services à domicile
    38: ('services',   'services-autres',    'non_applicable'),  # Lavage et repassage
}


# Rubriques TBG → liste des c_id PA
RUBRIQUE_TO_CATS = {
    'immobilier': [1, 2, 3, 4, 5, 6],
    'vehicules':  [9, 10, 11, 12, 13, 58, 59, 60],
    'occasion':   [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 33, 51, 52, 53, 54],
    'emploi':     [28, 29, 30],
    'services':   [32, 34, 36, 37, 38],
}

# Toutes les c_id confondues
ALL_CATEGORIES = sorted(PA_TO_TBG.keys())

# Aliases pour compatibilité
IMMOBILIER_CATEGORIES = RUBRIQUE_TO_CATS['immobilier']


def map_pa_category(c_id):
    """Renvoie (categorie, sous_categorie, type_transaction) pour un c_id PA.

    Renvoie None si la catégorie n'est pas mappée.
    """
    return PA_TO_TBG.get(int(c_id))


def cats_for_rubrique(rubrique):
    """Renvoie la liste des c_id PA pour une rubrique TBG.

    rubrique='all' ou None → toutes les catégories.
    """
    if not rubrique or rubrique == 'all':
        return ALL_CATEGORIES
    return RUBRIQUE_TO_CATS.get(rubrique, [])
