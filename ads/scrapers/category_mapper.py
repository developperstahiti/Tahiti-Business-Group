"""Table de correspondance entre les catégories de petites-annonces.pf et TBG.

Source PA : https://www.petites-annonces.pf/rss.php?c=N
Cible TBG : (categorie, sous_categorie, type_transaction)
"""

# c (param URL PA) → (categorie_tbg, sous_categorie_tbg, type_transaction_tbg)
PA_TO_TBG_IMMOBILIER = {
    1: ('immobilier', 'immo-appartements', 'vente'),     # Vends appartement
    2: ('immobilier', 'immo-maisons',      'vente'),     # Vends maison
    3: ('immobilier', 'immo-terrains',     'vente'),     # Vends terrain
    4: ('immobilier', 'immo-appartements', 'location'),  # Loue appartement
    5: ('immobilier', 'immo-maisons',      'location'),  # Loue maison
    6: ('immobilier', 'immo-saisonnieres', 'location'),  # Location saisonnière
}


def map_pa_category(c_id):
    """Renvoie (categorie, sous_categorie, type_transaction) pour un c_id PA.

    Renvoie None si la catégorie n'est pas mappée.
    """
    return PA_TO_TBG_IMMOBILIER.get(int(c_id))


IMMOBILIER_CATEGORIES = list(PA_TO_TBG_IMMOBILIER.keys())
