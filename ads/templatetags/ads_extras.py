from django import template

register = template.Library()

# Human-readable labels for spec keys stored in Annonce.specs
SPEC_LABELS = {
    # Véhicules
    'annee':           'Année',
    'kilometrage':     'Kilométrage',
    'carburant':       'Carburant',
    'boite':           'Boîte de vitesse',
    'nb_places':       'Places',
    'cylindree':       'Cylindrée',
    'permis':          'Permis requis',
    'longueur_m':      'Longueur',
    'moteur_hp':       'Puissance moteur',
    'type_bateau':     'Type de bateau',
    'charge_kg':       'Charge utile',
    'ptac_kg':         'PTAC',
    'marque':          'Marque',
    'modele':          'Modèle',
    'modele_compat':   'Modèle compatible',
    'annee_compat':    'Compatibilité (année)',
    # Immobilier
    'surface_m2':      'Surface',
    'terrain_m2':      'Terrain',
    'nb_pieces':       'Nb. pièces',
    'etage':           'Étage',
    'meuble':          'Meublé',
    'parking':         'Parking',
    'caution_xpf':     'Caution',
    'piscine':         'Piscine',
    'climatise':       'Climatisé',
    'viabilise':       'Viabilisé',
    'acces_route':     'Accès route',
    'zone':            'Zone',
    'nb_bureaux':      'Nb. bureaux',
    'ascenseur':       'Ascenseur',
    'nb_couchages':    'Couchages',
    'tarif_semaine':   'Tarif / semaine',
    'type_parking':    'Type de parking',
    'securise':        'Sécurisé',
    'acces_24h':       'Accès 24h/24',
    'loyer_mois':      'Loyer / mois',
    # Emploi
    'type_contrat':     'Contrat',
    'salaire_xpf':      'Salaire brut',
    'salaire_fixe':     'Salaire fixe',
    'salaire_variable': 'Variable / commissions',
    'salaire_jour':     'Salaire / jour',
    'heures_semaine':   'Heures / semaine',
    'experience_ans':   'Expérience requise',
    'permis_b':         'Permis B',
    'deplacements':     'Déplacements',
    'langages':         'Langages requis',
    'stack':            'Stack / framework',
    'remote_ok':        'Télétravail',
    'langues':          'Langues requises',
    'horaires':         'Horaires',
    'type_chantier':    'Type de chantier',
    'debut':            'Début souhaité',
    'diplome_requis':   'Diplôme requis',
    'references':       'Références exigées',
    'domicile':         'À domicile',
    # Électronique
    'stockage':         'Stockage',
    'ram_gb':           'RAM',
    'stockage_gb':      'Stockage',
    'processeur':       'Processeur',
    'os':               'Système',
    'gpu':              'Carte graphique',
    'usage':            'Usage principal',
    'refroidissement':  'Refroidissement',
    'facture':          'Facture incluse',
    'taille_pouces':    'Taille',
    'smart_tv':         'Smart TV',
    'resolution':       'Résolution',
    'console':          'Console',
    'jeux_inclus':      'Jeux inclus',
    'type_app':         "Type d'appareil",
    'notice':           'Notice incluse',
    'etat':             'État',
    # Services
    'type_travaux':     'Type de travaux',
    'devis_gratuit':    'Devis gratuit',
    'materiel':         'Matériel fourni',
    'deplacement':      'Zone de déplacement',
    'tva':              'Assujetti TVA',
    'matiere':          'Matière',
    'niveau':           'Niveau',
    'format':           'Format',
    'tarif_h':          'Tarif / heure',
    'type_trajet':      'Type de trajet',
    'capacite_kg':      'Capacité',
    'tarif_km':         'Tarif / km',
    'service':          'Type de service',
    'diplome':          'Diplômé(e)',
    'certificat':       'Certifié(e)',
    'frequence':        'Fréquence',
    # Autres
    'materiau':        'Matériau',
    'dimensions':      'Dimensions',
    'livraison':       'Livraison',
    'taille':          'Taille',
    'type_sport':      'Sport / activité',
    'age_enfant':      'Âge enfant',
}

SPEC_UNITS = {
    'kilometrage':      ' km',
    'surface_m2':       ' m²',
    'terrain_m2':       ' m²',
    'longueur_m':       ' m',
    'moteur_hp':        ' CV',
    'cylindree':        ' cc',
    'ram_gb':           ' Go',
    'stockage_gb':      ' Go',
    'taille_pouces':    '"',
    'loyer_mois':       ' XPF',
    'caution_xpf':      ' XPF',
    'tarif_semaine':    ' XPF',
    'salaire_xpf':      ' XPF',
    'salaire_fixe':     ' XPF',
    'salaire_variable': ' XPF',
    'salaire_jour':     ' XPF',
    'tarif_h':          ' XPF',
    'tarif_km':         ' XPF',
    'heures_semaine':   'h/sem',
    'experience_ans':   ' ans',
    'surface_m2':       ' m²',
}


@register.filter
def spec_label(key):
    return SPEC_LABELS.get(key, key.replace('_', ' ').capitalize())


@register.filter
def spec_value(val, key):
    unit = SPEC_UNITS.get(key, '')
    if unit and str(val).isdigit():
        return f"{int(val):,} {unit}".replace(',', '\u00a0').strip()
    return val


import re
from django.utils.safestring import mark_safe
from django.utils.html import escape


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Return current GET params with overrides, for pagination links.

    Usage: {% query_transform page=3 %}  ->  "categorie=immo&page=3&q=test"
    """
    request = context['request']
    updated = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None:
            updated[k] = v
        else:
            updated.pop(k, None)
    return updated.urlencode()

@register.filter(name='linkify')
def linkify(text):
    """Convert URLs in text to clickable links."""
    if not text:
        return text
    escaped = escape(text)
    url_pattern = re.compile(r'(https?://[^\s<>"{}|\\^`\[\]]+)')
    result = url_pattern.sub(
        r'<a href="\1" target="_blank" rel="nofollow noopener noreferrer" class="text-blue-600 hover:underline break-all">\1</a>',
        escaped
    )
    return mark_safe(result)
