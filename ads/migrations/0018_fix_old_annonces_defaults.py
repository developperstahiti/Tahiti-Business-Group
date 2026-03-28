"""
Data migration : appliquer des valeurs par défaut intelligentes
aux anciennes annonces créées avant les champs sous_categorie,
type_transaction, commune, etc.
"""
from django.db import migrations


def fix_old_annonces(apps, schema_editor):
    Annonce = apps.get_model('ads', 'Annonce')

    # ── 1. type_transaction pour immobilier ──────────────────────────────────
    # Mots-clés indiquant une location
    LOCATION_KW = [
        'louer', 'location', 'à louer', 'a louer', 'bail',
        'mensuel', 'par mois', '/mois', 'locataire',
    ]
    VENTE_KW = [
        'vendre', 'vente', 'à vendre', 'a vendre', 'achat',
        'acheter', 'cession',
    ]

    immo_ads = Annonce.objects.filter(
        categorie='immobilier',
        type_transaction='non_applicable',
    )
    for ad in immo_ads.iterator():
        titre_lower = ad.titre.lower()
        desc_lower = (ad.description or '').lower()[:500]
        text = titre_lower + ' ' + desc_lower

        is_location = any(kw in text for kw in LOCATION_KW)
        is_vente = any(kw in text for kw in VENTE_KW)

        if is_location and not is_vente:
            ad.type_transaction = 'location'
        elif is_vente and not is_location:
            ad.type_transaction = 'vente'
        else:
            # Ambiguous or no keyword — default to vente
            ad.type_transaction = 'vente'
        ad.save(update_fields=['type_transaction'])

    # ── 2. sous_categorie par défaut ─────────────────────────────────────────
    # Pour les annonces sans sous_categorie, on infère depuis le titre
    SOUS_CAT_RULES = {
        'immobilier': [
            ('immo-appartements', ['appartement', 'studio', 'f1', 'f2', 'f3', 'f4', 'f5', 'duplex']),
            ('immo-maisons', ['maison', 'villa', 'fare', 'bungalow', 'pavillon']),
            ('immo-terrains', ['terrain', 'lot', 'parcelle', 'foncier']),
            ('immo-bureaux', ['bureau', 'commerce', 'local', 'boutique', 'magasin', 'entrepôt', 'entrepot']),
            ('immo-saisonnieres', ['saisonni', 'vacance', 'airbnb', 'meublé', 'meuble', 'courte durée']),
            ('immo-parkings', ['parking', 'garage', 'box', 'stationnement']),
        ],
        'vehicules': [
            ('vehicules-voitures', ['voiture', 'auto', 'berline', 'suv', '4x4', 'pick-up', 'pickup', 'sedan']),
            ('vehicules-2roues', ['moto', 'scooter', '2 roues', 'deux roues', 'cyclo', 'quad']),
            ('vehicules-bateaux', ['bateau', 'jet-ski', 'jetski', 'pirogue', 'catamaran', 'hors-bord', 'zodiac']),
            ('vehicules-utilitaires', ['utilitaire', 'camion', 'fourgon', 'van', 'tracteur', 'engin']),
            ('vehicules-pieces', ['pièce', 'piece', 'accessoire', 'pneu', 'jante', 'pare-choc']),
        ],
        'occasion': [
            ('occasion-telephones', ['téléphone', 'telephone', 'iphone', 'samsung', 'smartphone', 'portable']),
            ('occasion-informatique', ['ordinateur', 'pc', 'laptop', 'macbook', 'imprimante', 'informatique']),
            ('occasion-tv', ['tv', 'télé', 'tele', 'écran', 'ecran', 'enceinte', 'sono', 'audio']),
            ('occasion-jeux-video', ['ps4', 'ps5', 'xbox', 'nintendo', 'switch', 'jeux vidéo', 'jeux video', 'console']),
            ('occasion-electromenager', ['frigo', 'machine à laver', 'lave-linge', 'four', 'micro-onde', 'climatiseur', 'clim']),
            ('occasion-meubles', ['meuble', 'canapé', 'canape', 'table', 'chaise', 'armoire', 'lit', 'matelas', 'étagère']),
            ('occasion-vetements', ['vêtement', 'vetement', 'chaussure', 'sac', 'robe', 'pantalon']),
            ('occasion-sport', ['sport', 'vélo', 'velo', 'surf', 'plongée', 'plongee', 'kayak', 'fitness']),
            ('occasion-puericulture', ['bébé', 'bebe', 'poussette', 'puériculture', 'puericulture']),
            ('occasion-jouets', ['jouet', 'lego', 'playmobil', 'poupée', 'peluche']),
        ],
        'emploi': [
            ('emploi-offre', ['recrute', 'recherchons', 'embauche', 'cdi', 'cdd', 'poste', 'offre d\'emploi']),
            ('emploi-recherche', ['recherche emploi', 'cherche emploi', 'disponible', 'cv', 'candidature']),
        ],
        'services': [
            ('services-travaux', ['travaux', 'btp', 'maçon', 'macon', 'plombier', 'électricien', 'electricien', 'peintre', 'carreleur', 'rénovation', 'renovation']),
            ('services-cours', ['cours', 'formation', 'soutien scolaire', 'professeur', 'tuteur']),
            ('services-transport', ['transport', 'déménagement', 'demenagement', 'livraison', 'chauffeur']),
            ('services-sante', ['santé', 'sante', 'beauté', 'beaute', 'massage', 'coiffure', 'esthétique']),
            ('services-jardinage', ['jardin', 'jardinage', 'tonte', 'élagage', 'elagage', 'paysagiste']),
        ],
    }

    # Fallback sous-catégorie par catégorie (quand aucun mot-clé ne matche)
    FALLBACK_SOUS_CAT = {
        'immobilier': 'immo-maisons',
        'vehicules': 'vehicules-voitures',
        'occasion': 'occasion-divers',
        'emploi': 'emploi-offre',
        'services': 'services-autres',
    }

    no_sous_cat = Annonce.objects.filter(sous_categorie='')
    for ad in no_sous_cat.iterator():
        rules = SOUS_CAT_RULES.get(ad.categorie, [])
        titre_lower = ad.titre.lower()
        desc_lower = (ad.description or '').lower()[:500]
        text = titre_lower + ' ' + desc_lower

        matched = None
        for sous_cat_code, keywords in rules:
            if any(kw in text for kw in keywords):
                matched = sous_cat_code
                break

        ad.sous_categorie = matched or FALLBACK_SOUS_CAT.get(ad.categorie, '')
        if ad.sous_categorie:
            ad.save(update_fields=['sous_categorie'])

    # ── 3. commune depuis localisation ───────────────────────────────────────
    # Les anciennes annonces ont localisation rempli mais commune vide
    no_commune = Annonce.objects.filter(commune='').exclude(localisation='')
    for ad in no_commune.iterator():
        ad.commune = ad.localisation.strip()
        if ad.commune:
            ad.save(update_fields=['commune'])

    # ── 4. Vérifier que les annonces admin sont bien actives ─────────────────
    # Les admins créent des annonces via l'admin Django — s'assurer qu'elles
    # sont visibles (statut='actif') sauf si explicitement modérées.
    Annonce.objects.filter(
        user__role='admin',
        statut='',
    ).update(statut='actif')


def reverse_noop(apps, schema_editor):
    """Pas de rollback — les valeurs par défaut sont non-destructives."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0017_alter_notation_unique_together_notation_avis_ecrit_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_old_annonces, reverse_noop),
    ]
