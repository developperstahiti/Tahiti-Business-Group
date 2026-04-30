import os
import re
import uuid
import datetime
import csv
import logging
from django.conf import settings as django_settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .decorators import staff_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models as db_models
from django.db.models import Q, Case, When, Value, IntegerField, Count
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.http import Http404, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Exists, OuterRef, Subquery
from django.views.decorators.http import require_POST
from .models import Annonce, Message, CATEGORIES, SOUS_CATEGORIES, Signalement, PRIX_UNITE_CHOICES, Enregistrement
from .image_utils import save_webp
from rubriques.models import ArticlePromo, ArticleInfo, ArticleNouveaute

User = get_user_model()
logger = logging.getLogger(__name__)


def _save_webp(file_obj, user_pk):
    """Upload une photo d'annonce en WebP 1200x900 + thumbnail 400x300.
    Retourne un tuple (url, thumb_url)."""
    return save_webp(file_obj, 'annonces', str(user_pk), max_size=(1200, 900), with_thumb=True)


_SPEC_KEY_RE = re.compile(r'^[a-z0-9_]{1,50}$')


def _clean_specs(post_data):
    """Extrait les champs spec_ du POST avec validation clé/valeur."""
    specs = {}
    for k, v in post_data.items():
        if not k.startswith('spec_'):
            continue
        key = k[5:]
        if not _SPEC_KEY_RE.match(key):
            continue
        value = v.strip()[:200]
        if value:
            specs[key] = value
        if len(specs) >= 20:
            break
    return specs


_HIDDEN_SOUS_CATS = {'services', 'occasion'}


def _sous_cats_data():
    return {
        cat: ([] if cat in _HIDDEN_SOUS_CATS
              else [{'value': v, 'label': l} for v, l in items])
        for cat, items in SOUS_CATEGORIES.items()
    }


def _get_communes_data():
    from .localites_polynesie import get_communes_by_archipel
    return get_communes_by_archipel()


def _get_quartiers_data():
    from .localites_polynesie import get_quartiers_by_commune
    return get_quartiers_by_commune()



def page_info(request):
    faq = [
        ("L'annonce est-elle vraiment gratuite ?",
         "Oui, 100 % gratuite. Créez un compte et publiez autant d'annonces que vous souhaitez sans aucun frais."),
        ("Combien de temps reste en ligne mon annonce ?",
         'Vos annonces restent actives 60 jours. Vous pouvez les renouveler à tout moment depuis "Mes annonces".'),
        ("Comment modifier ou supprimer mon annonce ?",
         'Connectez-vous, allez dans "Mes annonces", puis cliquez sur Modifier ou Supprimer.'),
        ("Quels types d'annonces puis-je publier ?",
         "Véhicules, immobilier, électronique, emploi, services et divers. Tout objet légal en Polynésie française."),
        ("Comment contacter un vendeur ?",
         "Cliquez sur le bouton \"Contacter\" sous l'annonce. Un chat privé s'ouvre directement sur le site."),
        ("Puis-je publier une annonce professionnelle ?",
         "Oui ! Les entreprises peuvent publier des offres d'emploi, recrutements ou services professionnels."),
        ("Comment fonctionne la publicité sur le site ?",
         "Nous proposons des emplacements banner (Billboard, Sidebar) visibles par tous les visiteurs. Tarifs dès 5 000 XPF/mois."),
        ("Mes données personnelles sont-elles sécurisées ?",
         "Oui. Votre email n'est jamais affiché publiquement. Les échanges entre acheteurs et vendeurs passent par notre messagerie sécurisée."),
        ("Je n'arrive pas à me connecter, que faire ?",
         'Utilisez "Mot de passe oublié" sur la page de connexion. Si le problème persiste, contactez-nous au 89 61 06 13.'),
        ("Puis-je vendre depuis les îles (Moorea, Bora Bora...) ?",
         "Bien sûr ! Tahiti Business Group couvre toute la Polynésie française : Tahiti, Moorea, Bora Bora, Raiatea, les Tuamotu et les Marquises."),
    ]
    return render(request, 'ads/info.html', {'faq': faq})


def page_business(request):
    ouvertures = [
        {'emoji': '🚗', 'nom': 'Auto-école Route 89', 'description': 'Nouvelle auto-école avec moniteurs bilingues français/tahitien.', 'secteur': 'Formation', 'lieu': 'Arue'},
        {'emoji': '🍜', 'nom': 'Poke Tahiti Mahina', 'description': 'Restaurant poke bowl avec produits locaux : thon, crevettes, légumes du fenua.', 'secteur': 'Restauration', 'lieu': 'Mahina'},
        {'emoji': '📺', 'nom': 'Hi-Fi Store Punaauia', 'description': "Magasin d'électronique grand public avec SAV et livraison sur Tahiti.", 'secteur': 'Électronique', 'lieu': 'Punaauia'},
        {'emoji': '💈', 'nom': 'Barbershop Papara', 'description': 'Salon de coiffure homme moderne avec réservation en ligne.', 'secteur': 'Beauté', 'lieu': 'Papara'},
        {'emoji': '🌿', 'nom': 'Jardinage Vert Fenua', 'description': "Service d'entretien jardins, taille, arrosage automatique.", 'secteur': 'Services', 'lieu': 'Papeete'},
        {'emoji': '🏋️', 'nom': 'FitZone Pirae', 'description': 'Nouvelle salle de sport avec équipements cardio et musculation dernière génération.', 'secteur': 'Sport', 'lieu': 'Pirae'},
    ]
    recrutements = [
        {'emoji': '🚕', 'poste': 'Chauffeurs VTC', 'entreprise': 'Tahiti Taxi Connect', 'lieu': 'Papeete', 'nb': 15, 'detail': 'Permis B requis, horaires flexibles, véhicule fourni.'},
        {'emoji': '💻', 'poste': 'Développeurs web', 'entreprise': 'Tahiti Informatique', 'lieu': "Faa'a", 'nb': 5, 'detail': 'Django/React, CDI, salaire selon expérience.'},
        {'emoji': '🏨', 'poste': 'Réceptionnistes', 'entreprise': 'Hotel Tara Nui', 'lieu': 'Bora Bora', 'nb': 3, 'detail': 'Anglais indispensable, logement possible sur place.'},
        {'emoji': '🏗️', 'poste': 'Maçons confirmés', 'entreprise': 'BTP Polynésie', 'lieu': 'Tahiti', 'nb': 8, 'detail': 'Expérience 3 ans minimum, chantiers résidentiels et commerciaux.'},
        {'emoji': '📦', 'poste': 'Livreurs', 'entreprise': 'Fenua Express', 'lieu': 'Tahiti + Moorea', 'nb': 10, 'detail': 'Scooter ou voiture, temps plein ou partiel disponible.'},
    ]
    tendances = [
        {'emoji': '🏠', 'titre': 'Immobilier Arue en hausse', 'desc': 'Les prix des terrains à Arue ont augmenté de 12 % en 2025. Forte demande résidentielle.'},
        {'emoji': '🚗', 'titre': "Véhicules d'occasion : marché actif", 'desc': 'Les annonces véhicules représentent 35 % du trafic TBG. Les 4x4 et SUV sont les plus recherchés.'},
        {'emoji': '📱', 'titre': 'Électronique reconditionné populaire', 'desc': 'Forte hausse des annonces smartphones reconditionnés. iPhone 13/14 dominent le marché.'},
        {'emoji': '💼', 'titre': 'Secteur BTP en pleine expansion', 'desc': "Nombreux chantiers publics et privés en cours. Forte demande en main-d'œuvre qualifiée."},
    ]
    partenaires = [
        {'emoji': '🛒', 'nom': 'Carrefour Tahiti', 'secteur': 'Grande distribution'},
        {'emoji': '📡', 'nom': 'Vini', 'secteur': 'Télécoms'},
        {'emoji': '🏦', 'nom': 'Banque de Polynésie', 'secteur': 'Finance'},
        {'emoji': '✈️', 'nom': 'Air Tahiti Nui', 'secteur': 'Transport aérien'},
        {'emoji': '🏥', 'nom': 'Clinique Paofai', 'secteur': 'Santé'},
        {'emoji': '🎓', 'nom': 'UPF', 'secteur': 'Université'},
        {'emoji': '🔧', 'nom': 'Total Polynésie', 'secteur': 'Énergie'},
        {'emoji': '🌺', 'nom': 'Office du Tourisme', 'secteur': 'Tourisme'},
    ]
    return render(request, 'ads/business.html', {
        'ouvertures': ouvertures,
        'recrutements': recrutements,
        'tendances': tendances,
        'partenaires': partenaires,
    })

def _apply_boost_sort(qs):
    """Annote et trie un queryset : boosts actifs non expirés en premier."""
    now = timezone.now()
    return qs.annotate(
        _boost_rank=Case(
            When(
                Q(boost=True) & (Q(boost_expires_at__isnull=True) | Q(boost_expires_at__gt=now)),
                then=Value(1)
            ),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('-_boost_rank', '-updated_at')


def _annotate_enregistrements(qs, user):
    """Annote un queryset d'annonces avec le compteur d'enregistrements
    et un booleen is_enregistre pour l'utilisateur courant."""
    qs = qs.annotate(enregistrement_count=Count('enregistrements'))
    if user.is_authenticated:
        qs = qs.annotate(
            is_enregistre=Exists(
                Enregistrement.objects.filter(user=user, annonce=OuterRef('pk'))
            )
        )
    return qs


def index(request):
    base = Annonce.objects.filter(statut='actif').select_related('user', 'user__profil')
    base = _annotate_enregistrements(base, request.user)
    qs = _apply_boost_sort(base)
    annonces_recentes = qs[:10]
    total_count = Annonce.objects.filter(statut='actif').count()

    # Ordre d'affichage aligné sur la nav
    cat_order = ['immobilier', 'vehicules', 'occasion', 'emploi', 'services']
    cat_labels = dict(CATEGORIES)
    annonces_par_cat = []
    for code in cat_order:
        cat_qs = _apply_boost_sort(
            _annotate_enregistrements(
                Annonce.objects.filter(statut='actif', categorie=code).select_related('user', 'user__profil'),
                request.user,
            )
        )
        annonces_par_cat.append({
            'code': code,
            'label': cat_labels[code],
            'annonces': list(cat_qs[:10]),
        })

    promos_home     = ArticlePromo.objects.filter(statut='valide').select_related('pro_user')[:10]
    infos_home      = ArticleInfo.objects.filter(statut='valide').select_related('auteur')[:4]
    nouveautes_home = ArticleNouveaute.objects.filter(statut='valide').select_related('pro_user')[:4]

    return render(request, 'ads/index.html', {
        'annonces_recentes': annonces_recentes,
        'annonces_par_cat':  annonces_par_cat,
        'categories':        CATEGORIES,
        'total_count':       total_count,
        'promos_home':       promos_home,
        'infos_home':        infos_home,
        'nouveautes_home':   nouveautes_home,
    })


_PRETRIAGE_IMMOBILIER = [
    ('Appartements à louer',  {'sous_categorie': 'immo-appartements', 'type_transaction': 'location'}, 'sous_cat=immo-appartements&transaction=location'),
    ('Appartements à vendre', {'sous_categorie': 'immo-appartements', 'type_transaction': 'vente'},    'sous_cat=immo-appartements&transaction=vente'),
    ('Maisons à louer',       {'sous_categorie': 'immo-maisons', 'type_transaction': 'location'},      'sous_cat=immo-maisons&transaction=location'),
    ('Maisons à vendre',      {'sous_categorie': 'immo-maisons', 'type_transaction': 'vente'},         'sous_cat=immo-maisons&transaction=vente'),
    ('Terrains à vendre',     {'sous_categorie': 'immo-terrains'},                                     'sous_cat=immo-terrains'),
    ('Bureaux et commerces',  {'sous_categorie': 'immo-bureaux'},                                      'sous_cat=immo-bureaux'),
    ('Saisonnières',          {'sous_categorie': 'immo-saisonnieres'},                                 'sous_cat=immo-saisonnieres'),
    ('Parkings et garages',   {'sous_categorie': 'immo-parkings'},                                     'sous_cat=immo-parkings'),
]

_PRETRIAGE_VEHICULES = [
    ('Voitures',                  {'sous_categorie': 'vehicules-voitures'},    'sous_cat=vehicules-voitures'),
    ('2 roues (scooters/motos)',  {'sous_categorie': 'vehicules-2roues'},      'sous_cat=vehicules-2roues'),
    ('Bateaux et jet-skis',      {'sous_categorie': 'vehicules-bateaux'},     'sous_cat=vehicules-bateaux'),
    ('Utilitaires et camions',   {'sous_categorie': 'vehicules-utilitaires'}, 'sous_cat=vehicules-utilitaires'),
    ('Pièces et accessoires',    {'sous_categorie': 'vehicules-pieces'},      'sous_cat=vehicules-pieces'),
]

def _pretriage_from_sous_cats(cat_code):
    """Génère un pré-triage basé sur SOUS_CATEGORIES."""
    return [
        (label, {'sous_categorie': code}, f'sous_cat={code}')
        for code, label in SOUS_CATEGORIES.get(cat_code, [])
    ]

_PRETRIAGE_MAP = {
    'immobilier': _PRETRIAGE_IMMOBILIER,
    'vehicules':  _PRETRIAGE_VEHICULES,
    'occasion':   [],
    'services':   [],
}


def _build_pretriage_groups(cat, base_qs, limit=10):
    """Construit les groupes de pré-triage pour une catégorie."""
    groups_def = _PRETRIAGE_MAP.get(cat) if cat in _PRETRIAGE_MAP else _pretriage_from_sous_cats(cat)
    groups = []
    for label, filters, qs_params in groups_def:
        group_qs = base_qs.filter(**filters)
        total = group_qs.count()
        if total == 0:
            continue
        groups.append({
            'label': label,
            'annonces': list(group_qs[:limit]),
            'total': total,
            'filter_url': f'?categorie={cat}&{qs_params}',
        })
    return groups


def liste_annonces(request):
    qs = _annotate_enregistrements(
        Annonce.objects.filter(statut='actif').select_related('user', 'user__profil'),
        request.user,
    )
    q        = request.GET.get('q', '')
    cat      = request.GET.get('categorie', '')
    sous_cat = request.GET.get('sous_cat', '')
    ville    = request.GET.get('localisation', '')
    prix_min = request.GET.get('prix_min', '')
    prix_max = request.GET.get('prix_max', '')
    tri      = request.GET.get('tri', '')
    transaction = request.GET.get('transaction', '')

    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(description__icontains=q))
        # Prioritise title matches over description-only matches
        qs = qs.annotate(
            _title_match=Case(
                When(titre__icontains=q, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
    if cat:
        qs = qs.filter(categorie=cat)
    if sous_cat:
        qs = qs.filter(sous_categorie=sous_cat)
    if transaction:
        qs = qs.filter(type_transaction=transaction)
    if ville:
        # Support multi-localisation (valeurs séparées par virgule)
        locs = [v.strip() for v in ville.split(',') if v.strip()]
        if len(locs) == 1:
            v = locs[0]
            qs = qs.filter(
                Q(commune__icontains=v) | Q(quartier__icontains=v) | Q(localisation__icontains=v)
            )
        elif locs:
            loc_q = Q()
            for v in locs:
                loc_q |= Q(commune__icontains=v) | Q(quartier__icontains=v) | Q(localisation__icontains=v)
            qs = qs.filter(loc_q)
    if prix_min:
        try:
            qs = qs.filter(prix__gte=int(prix_min))
        except ValueError:
            pass
    if prix_max:
        try:
            qs = qs.filter(prix__lte=int(prix_max))
        except ValueError:
            pass

    # Filtre photos uniquement
    if request.GET.get('photos'):
        qs = qs.exclude(photos=[])

    # Filtre comptes pro uniquement
    if request.GET.get('pro'):
        qs = qs.filter(user__role__in=['pro', 'admin'])

    # Prefix for search-relevance: title matches first when a query is active
    _search_prefix = ('_title_match',) if q else ()

    if tri == 'prix_asc':
        qs = qs.order_by(*_search_prefix, 'prix')
    elif tri == 'prix_desc':
        qs = qs.order_by(*_search_prefix, '-prix')
    elif tri == 'recent':
        qs = qs.order_by(*_search_prefix, '-created_at')
    elif tri == 'vues':
        qs = qs.order_by(*_search_prefix, '-views')
    elif tri == 'clics':
        qs = qs.order_by(*_search_prefix, '-clics')
    elif tri == 'ancien':
        qs = qs.order_by(*_search_prefix, 'created_at')
    else:
        qs = _apply_boost_sort(qs)
        if q:
            # Re-order so title-match priority comes before boost rank
            qs = qs.order_by('_title_match', '-_boost_rank', '-updated_at')

    # Sous-catégories disponibles pour la catégorie active
    sous_cats_dispo = SOUS_CATEGORIES.get(cat, []) if (cat and cat not in _HIDDEN_SOUS_CATS) else []

    # Pré-triage : grouper par sous-cat quand aucun filtre n'est actif
    has_filters = any([q, sous_cat, ville, prix_min, prix_max, transaction,
                       request.GET.get('photos'), request.GET.get('pro'), tri])
    pretriage_groups = []
    if cat and not has_filters and not request.GET.get('page'):
        pretriage_groups = _build_pretriage_groups(cat, qs)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    # Partial response for "load more" AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = ''.join(
            render_to_string('partials/_annonce_card.html', {'annonce': a}, request=request)
            for a in page
        )
        return JsonResponse({
            'html': html,
            'has_next': page.has_next(),
            'next_page': page.next_page_number() if page.has_next() else None,
        })

    # Pubs spécifiques à la catégorie (3 strips : haut, milieu, bas)
    from pubs.models import Publicite
    _CAT_STRIP_PREFIX = {
        'immobilier': 'strip_immo',
        'vehicules':  'strip_vehicules',
        'occasion':   'strip_occasion',
        'emploi':     'strip_emploi',
        'services':   'strip_services',
    }
    pub_cat_haut = pub_cat_milieu = pub_cat_bas = None
    strip_prefix = _CAT_STRIP_PREFIX.get(cat, '')
    cat_label_map = dict(CATEGORIES)
    strip_cat_label = cat_label_map.get(cat, '')
    if strip_prefix:
        pub_cat_haut   = Publicite.objects.filter(emplacement=f'{strip_prefix}_haut',   actif=True).first()
        pub_cat_milieu = Publicite.objects.filter(emplacement=f'{strip_prefix}_milieu', actif=True).first()
        pub_cat_bas    = Publicite.objects.filter(emplacement=f'{strip_prefix}_bas',    actif=True).first()

    return render(request, 'ads/liste.html', {
        'annonces':        page,
        'categories':      CATEGORIES,
        'q':               q,
        'cat_active':      cat,
        'sous_cat':        sous_cat,
        'sous_cats_dispo': sous_cats_dispo,
        'sous_cats_data':  _sous_cats_data(),
        'ville':           ville,
        'prix_min':        prix_min,
        'prix_max':        prix_max,
        'tri':             tri,
        'photos_only':     request.GET.get('photos', ''),
        'transaction':     transaction,
        'communes_par_archipel': _get_communes_data(),
        'pub_cat_haut':   pub_cat_haut,
        'pub_cat_milieu': pub_cat_milieu,
        'pub_cat_bas':    pub_cat_bas,
        'strip_prefix':   strip_prefix,
        'strip_cat_label': strip_cat_label,
        'pretriage_groups': pretriage_groups,
        'active_filters_count': sum(1 for v in [
            request.GET.get('sous_cat'), request.GET.get('ville'),
            request.GET.get('prix_min'), request.GET.get('prix_max'),
            request.GET.get('photos'), request.GET.get('transaction'),
            request.GET.get('q'),
        ] if v),
    })


def annonce_detail_redirect(request, pk):
    """Redirection 301 depuis l'ancienne URL /annonces/<pk>/ vers /annonces/<pk>/<slug>/."""
    annonce = get_object_or_404(Annonce, pk=pk)
    return redirect(annonce.get_absolute_url(), permanent=True)


def annonce_detail(request, pk, slug=''):
    from .notation_utils import stats_vendeur, peut_noter

    annonce = get_object_or_404(Annonce.objects.select_related('user', 'user__profil'), pk=pk)

    # Si le slug ne correspond pas, rediriger 301 vers le bon slug
    if slug != annonce.slug:
        return redirect(annonce.get_absolute_url(), permanent=True)

    # Seuls les annonces actives sont visibles publiquement ;
    # le propriétaire et les admins peuvent voir toute annonce.
    is_owner = request.user.is_authenticated and request.user == annonce.user
    is_admin = request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin'
    if annonce.statut != 'actif' and not is_owner and not is_admin:
        raise Http404
    annonce.increment_clics()

    if request.method == 'POST' and request.user.is_authenticated and annonce.user != request.user:
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                annonce=annonce,
                from_user=request.user,
                to_user=annonce.user,
                content=content,
            )
            messages.success(request, "Votre message a bien été envoyé !")
            return redirect(annonce.get_absolute_url())

    # Compteur d'enregistrements
    enregistrement_count = Enregistrement.objects.filter(annonce=annonce).count()
    is_enregistre = False
    if request.user.is_authenticated:
        is_enregistre = Enregistrement.objects.filter(user=request.user, annonce=annonce).exists()

    annonces_similaires = _annotate_enregistrements(
        Annonce.objects.filter(
            statut='actif', categorie=annonce.categorie
        ).exclude(pk=pk).select_related('user', 'user__profil'),
        request.user,
    )[:4]

    vendeur_stats = stats_vendeur(annonce.user)
    peut_noter_vendeur = False
    if request.user.is_authenticated and request.user != annonce.user:
        peut_noter_vendeur = peut_noter(request.user, annonce.user)

    return render(request, 'ads/detail.html', {
        'annonce':              annonce,
        'enregistrement_count': enregistrement_count,
        'is_enregistre':        is_enregistre,
        'annonces_similaires':  annonces_similaires,
        'vendeur_stats':        vendeur_stats,
        'peut_noter_vendeur':   peut_noter_vendeur,
    })


@login_required
def deposer_annonce(request):
    from .forms import AnnonceForm

    if request.method == 'POST':
        logger.info("=== DEPOSER POST === FILES keys=%s, FILES count=%s",
                    list(request.FILES.keys()),
                    sum(len(request.FILES.getlist(k)) for k in request.FILES))
        for k in request.FILES:
            for f in request.FILES.getlist(k):
                logger.info("  FILE: name=%s key=%s size=%s content_type=%s", f.name, k, f.size, f.content_type)
        form = AnnonceForm(request.POST, request.FILES)
        if form.is_valid():
            annonce = form.save(commit=False)
            annonce.user = request.user
            annonce.sous_categorie = request.POST.get('sous_categorie', '')
            # Localisation structuree
            annonce.commune = request.POST.get('commune', '')
            annonce.quartier = request.POST.get('quartier', '')
            annonce.precision_lieu = request.POST.get('precision_lieu', '')
            if annonce.commune:
                annonce.localisation = annonce.commune
            # Vente / Location (immobilier uniquement)
            if annonce.categorie == 'immobilier':
                annonce.type_transaction = request.POST.get('type_transaction', 'vente')
            else:
                annonce.type_transaction = 'non_applicable'
            annonce.specs = _clean_specs(request.POST)
            photos = []
            thumbs = []
            for f in request.FILES.getlist('photos')[:5]:
                try:
                    url, thumb_url = _save_webp(f, request.user.pk)
                    logger.info("Photo sauvegardée OK: %s (thumb: %s)", url, thumb_url)
                    photos.append(url)
                    thumbs.append(thumb_url)
                except Exception as e:
                    logger.error("Erreur upload photo annonce: %s", e, exc_info=True)
            logger.info("=== PHOTOS FINAL: %d photo(s) => %s", len(photos), photos)
            annonce.photos = photos
            annonce.photos_thumbs = thumbs

            # ── Boost (payant uniquement) ───────────────────────────────────
            boost_duree   = request.POST.get('boost_duree', '').strip()
            boost_demande = request.POST.get('boost_demande', '').strip()

            if boost_duree == '7jours':
                annonce.boost_duree   = '7jours'
                annonce.boost_status  = 'pending'
                annonce.boost_demande = boost_demande
            elif boost_duree == '1mois':
                annonce.boost_duree   = '1mois'
                annonce.boost_status  = 'pending'
                annonce.boost_demande = boost_demande

            annonce.save()

            # Notifier les utilisateurs avec une alerte correspondante
            from .models import AlerteAnnonce

            alertes = AlerteAnnonce.objects.filter(categorie=annonce.categorie)
            if annonce.sous_categorie:
                alertes = alertes.filter(
                    db_models.Q(sous_categorie='') | db_models.Q(sous_categorie=annonce.sous_categorie)
                )
            # Max 1 email par jour par alerte
            yesterday = timezone.now() - datetime.timedelta(days=1)
            alertes = alertes.filter(
                db_models.Q(derniere_notification__isnull=True) | db_models.Q(derniere_notification__lt=yesterday)
            ).exclude(user=request.user)

            for alerte in alertes[:50]:  # Limiter à 50 notifications
                try:
                    send_mail(
                        subject=f'Nouvelle annonce {annonce.get_categorie_display()} — TBG',
                        message=(
                            f'Bonjour {alerte.user.nom or ""},\n\n'
                            f'Une nouvelle annonce correspond à votre alerte :\n\n'
                            f'"{annonce.titre}"\n'
                            f'Prix : {annonce.get_prix_display_label()}\n'
                            f'Lieu : {annonce.localisation}\n\n'
                            f'Voir l\'annonce :\n'
                            f'https://www.tahitibusinessgroup.com/annonces/{annonce.pk}/\n\n'
                            f'— Tahiti Business Group'
                        ),
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[alerte.user.email],
                        fail_silently=True,
                    )
                    alerte.derniere_notification = timezone.now()
                    alerte.save(update_fields=['derniere_notification'])
                except Exception as e:
                    logger.error("Erreur envoi alerte email: %s", e)

            # Email de confirmation de publication
            try:
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags

                html_msg = render_to_string('emails/annonce_publiee.html', {
                    'nom': request.user.nom or 'membre',
                    'annonce_titre': annonce.titre,
                    'categorie': annonce.get_categorie_display(),
                    'prix': annonce.get_prix_display_label(),
                    'annonce_pk': annonce.pk,
                    'annonce_slug': annonce.slug,
                })
                send_mail(
                    subject=f'Votre annonce "{annonce.titre}" est en ligne sur TBG',
                    message=strip_tags(html_msg),
                    from_email=None,
                    recipient_list=[request.user.email],
                    html_message=html_msg,
                    fail_silently=True,
                )
            except Exception as e:
                logger.error("Erreur envoi email confirmation publication: %s", e)

            if boost_duree in ('7jours', '1mois'):
                # Renvoyer une URL JSON pour que le JS redirige vers le paiement
                annonce.boost_payment_ref = f"BOOST{uuid.uuid4().hex[:8].upper()}"
                annonce.save(update_fields=['boost_payment_ref'])
                request.session['boost_pending_pk'] = annonce.pk
                from django.urls import reverse
                return JsonResponse({
                    'redirect': reverse('boost_paiement', kwargs={'pk': annonce.pk})
                })
            else:
                messages.success(request, f"Annonce publiée ! {len(photos)} photo(s) ajoutée(s).")
            return redirect(annonce.get_absolute_url())
    else:
        form = AnnonceForm()

    from .localites_polynesie import get_communes_by_archipel
    return render(request, 'ads/deposer.html', {
        'form':               form,
        'sous_categories_data': _sous_cats_data(),
        'communes_par_archipel': get_communes_by_archipel(),
        'quartiers_par_commune': _get_quartiers_data(),
    })


@login_required
def mes_annonces(request):
    qs = Annonce.objects.filter(user=request.user).select_related('user', 'user__profil')
    statut = request.GET.get('statut', '')
    if statut in ('actif', 'vendu', 'en_attente'):
        qs = qs.filter(statut=statut)
    annonces = qs.order_by('-created_at')
    return render(request, 'ads/mes_annonces.html', {'annonces': annonces, 'statut_filter': statut})


@login_required
def edit_annonce(request, pk):
    # Admins peuvent éditer toutes les annonces
    if request.user.is_staff:
        annonce = get_object_or_404(Annonce, pk=pk)
    else:
        annonce = get_object_or_404(Annonce, pk=pk, user=request.user)

    if request.method == 'POST':
        annonce.titre          = request.POST.get('titre', '').strip() or annonce.titre
        annonce.description    = request.POST.get('description', '').strip() or annonce.description
        annonce.categorie      = request.POST.get('categorie', annonce.categorie)
        annonce.sous_categorie = request.POST.get('sous_categorie', '')
        new_specs = _clean_specs(request.POST)
        if new_specs:
            annonce.specs = new_specs
        annonce.commune        = request.POST.get('commune', '')
        annonce.quartier       = request.POST.get('quartier', '')
        annonce.precision_lieu = request.POST.get('precision_lieu', '')
        annonce.localisation   = annonce.commune or request.POST.get('localisation', '').strip() or annonce.localisation
        annonce.prix_label       = request.POST.get('prix_label', '').strip()
        annonce.prix_unite       = request.POST.get('prix_unite', '')
        annonce.type_transaction = request.POST.get('type_transaction', annonce.type_transaction)
        try:
            annonce.prix = int(request.POST.get('prix', 0) or 0)
        except (ValueError, TypeError):
            annonce.prix = 0

        # Champs réservés aux admins
        if request.user.is_staff:
            new_statut = request.POST.get('statut', '')
            if new_statut in ('actif', 'inactif', 'vendu'):
                annonce.statut = new_statut
            annonce.verified = request.POST.get('verified') == '1'

        # Supprimer les photos cochées (et leurs thumbnails associés)
        to_delete = request.POST.getlist('delete_photos')
        # Construire une map index→url pour synchroniser photos_thumbs
        old_photos = annonce.photos
        old_thumbs = list(annonce.photos_thumbs) if annonce.photos_thumbs else []
        # Padder thumbs si nécessaire (annonces sans thumbnails existants)
        while len(old_thumbs) < len(old_photos):
            old_thumbs.append(None)

        current = []
        current_thumbs = []
        for i, p in enumerate(old_photos):
            if p not in to_delete:
                current.append(p)
                current_thumbs.append(old_thumbs[i])
            else:
                # Tenter de supprimer le fichier local (ignoré pour S3)
                try:
                    rel  = p.replace(django_settings.MEDIA_URL, '')
                    path = os.path.join(django_settings.MEDIA_ROOT, rel)
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as e:
                    logger.error("Erreur suppression photo: %s", e)

        # Réordonner les photos existantes selon l'ordre envoyé
        photo_order = request.POST.getlist('photo_order')
        if photo_order:
            ordered = []
            ordered_thumbs = []
            for url in photo_order:
                if url in current:
                    idx = current.index(url)
                    ordered.append(url)
                    ordered_thumbs.append(current_thumbs[idx])
            # Ajouter les photos pas dans l'ordre (sécurité)
            for i, url in enumerate(current):
                if url not in ordered:
                    ordered.append(url)
                    ordered_thumbs.append(current_thumbs[i])
            current = ordered
            current_thumbs = ordered_thumbs

        # Ajouter nouvelles photos (max 5 total)
        for photo_file in request.FILES.getlist('photos'):
            if len(current) >= 5:
                break
            try:
                url, thumb_url = _save_webp(photo_file, request.user.pk)
                current.append(url)
                current_thumbs.append(thumb_url)
            except Exception as e:
                logger.error("Erreur upload nouvelle photo: %s", e)

        annonce.photos = current
        annonce.photos_thumbs = current_thumbs
        annonce.save()
        messages.success(request, "Annonce modifiée avec succès.")
        return redirect(annonce.get_absolute_url())

    return render(request, 'ads/edit_annonce.html', {
        'annonce':              annonce,
        'categories':           CATEGORIES,
        'prix_unite_choices':   PRIX_UNITE_CHOICES,
        'sous_categories_data': _sous_cats_data(),
        'remaining_slots':      max(0, 5 - len(annonce.photos)),
        'communes_par_archipel': _get_communes_data(),
        'quartiers_par_commune': _get_quartiers_data(),
    })


@login_required
def supprimer_annonce(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk, user=request.user)
    if request.method == 'POST':
        for photo_url in annonce.photos:
            try:
                rel  = photo_url.replace(django_settings.MEDIA_URL, '')
                path = os.path.join(django_settings.MEDIA_ROOT, rel)
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.error("Erreur suppression photo annonce: %s", e)
        annonce.delete()
        messages.success(request, "Annonce supprimée.")
    return redirect('mes_annonces')


@login_required
def marquer_vendu(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk, user=request.user)
    annonce.statut = 'vendu'
    annonce.save()
    messages.success(request, "Annonce marquée comme vendue.")
    return redirect('mes_annonces')


@login_required
def remonter_annonces(request):
    """Republier les annonces selectionnees (delai 24h entre chaque republication)."""
    if request.method != 'POST':
        return redirect('mes_annonces')

    ids = request.POST.getlist('annonce_ids')
    if not ids:
        messages.warning(request, "Aucune annonce selectionnee.")
        return redirect('mes_annonces')

    annonces = Annonce.objects.filter(pk__in=ids, user=request.user, statut='actif')
    now = timezone.now()
    remontees = 0
    bloquees = []

    for a in annonces:
        if a.derniere_remontee and (now - a.derniere_remontee).total_seconds() < 86400:
            reste = 86400 - (now - a.derniere_remontee).total_seconds()
            heures = int(reste // 3600)
            minutes = int((reste % 3600) // 60)
            bloquees.append(f'"{a.titre}" (encore {heures}h{minutes:02d})')
        else:
            a.updated_at = now  # auto_now empeche le set direct, on passe par save()
            a.derniere_remontee = now
            Annonce.objects.filter(pk=a.pk).update(updated_at=now, derniere_remontee=now)
            remontees += 1

    if remontees:
        messages.success(request, f"{remontees} annonce(s) republiée(s) avec succès.")
    if bloquees:
        messages.warning(request, f"Annonces non republiées (délai 24h) : {', '.join(bloquees)}")

    return redirect('mes_annonces')


def contact_annonce(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Connectez-vous pour contacter ce vendeur', 'auth_required': True}, status=403)

    try:
        annonce = Annonce.objects.get(pk=pk)
    except Annonce.DoesNotExist:
        return JsonResponse({'error': 'Annonce introuvable'}, status=404)

    User = get_user_model()

    # Le vendeur peut voir ses conversations avec les acheteurs via ?with=<pk>
    if annonce.user == request.user:
        other_pk = request.GET.get('with')
        if not other_pk:
            return JsonResponse({'error': 'Paramètre manquant'}, status=400)
        try:
            buyer = User.objects.get(pk=other_pk)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur introuvable'}, status=404)
        seller = request.user
    else:
        buyer = request.user
        seller = annonce.user

    thread = Message.objects.filter(annonce=annonce).filter(
        Q(from_user=buyer, to_user=seller) |
        Q(from_user=seller, to_user=buyer)
    ).order_by('created_at').select_related('from_user', 'to_user')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if len(content) < 1:
            return JsonResponse({'error': 'Message vide'}, status=400)
        content = content[:2000]
        to_user = buyer if request.user == seller else seller
        msg = Message.objects.create(
            annonce=annonce,
            from_user=request.user,
            to_user=to_user,
            content=content,
        )
        # Email notification au vendeur
        try:
            html_msg = render_to_string('emails/nouveau_message.html', {
                'vendeur_nom': annonce.user.nom or 'vendeur',
                'annonce_titre': annonce.titre,
                'acheteur_nom': msg.from_user.nom or msg.from_user.email,
                'message_preview': msg.content[:60] + ('...' if len(msg.content) > 60 else ''),
            })
            from django.utils.html import strip_tags
            send_mail(
                subject=f'Nouveau message pour votre annonce "{annonce.titre}" — TBG',
                message=strip_tags(html_msg),
                from_email=None,
                recipient_list=[annonce.user.email],
                html_message=html_msg,
                fail_silently=True,
            )
        except Exception as e:
            logger.error("Erreur envoi email notification message: %s", e)
        thread.filter(from_user=to_user, read=False).update(read=True)
        try:
            html = render_to_string(
                'partials/_message_bubble.html',
                {'msg': msg, 'me': request.user},
                request=request,
            )
        except Exception as e:
            logger.error("Erreur render _message_bubble: %s", e)
            from django.utils.html import escape as html_escape
            html = (
                '<div class="chat-bubble chat-bubble--me">'
                '<div class="chat-bubble__text">' + html_escape(msg.content) + '</div>'
                '<div class="chat-bubble__time">maintenant</div>'
                '</div>'
            )
        return JsonResponse({'success': True, 'html': html})

    # GET → mark received messages as read, return modal HTML
    thread.filter(to_user=request.user, read=False).update(read=True)
    with_pk = request.GET.get('with')
    try:
        html = render_to_string(
            'ads/contact_modal.html',
            {'annonce': annonce, 'thread': thread, 'with_pk': with_pk},
            request=request,
        )
    except Exception as e:
        logger.error("Erreur render contact_modal: %s", e)
        return JsonResponse({'error': 'Erreur interne, veuillez réessayer'}, status=500)
    return JsonResponse({'html': html})


@login_required
def mes_messages(request):
    all_msgs = Message.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).select_related('annonce', 'from_user', 'to_user').order_by('-created_at')

    # One conversation entry per (annonce, other_user) pair
    seen = set()
    conversations = []
    for msg in all_msgs:
        other = msg.to_user if msg.from_user == request.user else msg.from_user
        key = (msg.annonce_id, other.pk)
        if key not in seen:
            seen.add(key)
            unread = Message.objects.filter(
                annonce=msg.annonce, to_user=request.user, from_user=other, read=False
            ).count()
            conversations.append({
                'annonce':    msg.annonce,
                'last_msg':   msg,
                'other_user': other,
                'unread':     unread,
            })

    # Mark all as read now that user is viewing
    Message.objects.filter(to_user=request.user, read=False).update(read=True)

    return render(request, 'ads/mes_messages.html', {'conversations': conversations})


@login_required
@require_POST
def supprimer_conversation(request, annonce_pk, other_user_pk):
    User = get_user_model()
    other = get_object_or_404(User, pk=other_user_pk)
    Message.objects.filter(
        annonce_id=annonce_pk
    ).filter(
        Q(from_user=request.user, to_user=other) |
        Q(from_user=other, to_user=request.user)
    ).delete()
    return redirect('mes_messages')


# ── Impressions (vues au scroll) ──────────────────────────────────────────
from django.views.decorators.http import require_POST
import json


@require_POST
def track_impressions(request):
    """Incremente les vues des annonces visibles a l'ecran (batch).

    Appel AJAX depuis le navigateur — CSRF token requis dans le header X-CSRFToken.
    """
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return JsonResponse({'ok': False})
        # Max 50 par requete pour eviter les abus
        ids = [int(i) for i in ids[:50]]
        from django.db.models import F
        Annonce.objects.filter(pk__in=ids, statut='actif').update(views=F('views') + 1)
        return JsonResponse({'ok': True, 'count': len(ids)})
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'ok': False}, status=400)


# ── Rate limiting (session-based) ─────────────────────────────────────────
def _rate_limited(request, action, max_count=3, period_minutes=60):
    key = f'rl_{action}'
    now = datetime.datetime.now().timestamp()
    cutoff = now - period_minutes * 60
    history = [t for t in request.session.get(key, []) if t > cutoff]
    if len(history) >= max_count:
        return True
    history.append(now)
    request.session[key] = history
    request.session.modified = True
    return False


# ── Toggle enregistrement (AJAX) ─────────────────────────────────────────
@require_POST
def toggle_enregistrement(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Non connecté'}, status=403)
    import json
    try:
        data = json.loads(request.body)
        annonce_id = int(data.get('annonce_id', 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        annonce_id = int(request.POST.get('annonce_id', 0))
    annonce = get_object_or_404(Annonce, pk=annonce_id)
    obj, created = Enregistrement.objects.get_or_create(user=request.user, annonce=annonce)
    if not created:
        obj.delete()
    count = Enregistrement.objects.filter(annonce=annonce).count()
    return JsonResponse({
        'saved': created,
        'count': count,
    })


# ── Mes Favoris / Mes annonces enregistrees ──────────────────────────────
def mes_favoris(request):
    annonces = []
    # Priorite 1 : utilisateur connecte → base de donnees
    if request.user.is_authenticated:
        annonces = list(
            Annonce.objects.filter(
                enregistrements__user=request.user,
                statut='actif',
            ).select_related('user', 'user__profil')
            .annotate(enregistrement_count=Count('enregistrements'))
            .order_by('-enregistrements__date_creation')
        )
    # Fallback localStorage (ids en parametre GET)
    if not annonces:
        ids_raw = request.GET.get('ids', '')
        if ids_raw:
            try:
                pk_list = [int(x.strip()) for x in ids_raw.split(',') if x.strip().isdigit()][:50]
                annonces = list(Annonce.objects.filter(pk__in=pk_list, statut='actif').select_related('user', 'user__profil')
                                .annotate(enregistrement_count=Count('enregistrements')))
            except (ValueError, TypeError):
                pass
    return render(request, 'ads/mes_favoris.html', {'annonces': annonces})


# ── Signaler une annonce ─────────────────────────────────────────────────
@login_required
def signaler_annonce(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk, statut='actif')
    if request.method == 'POST':
        raison  = request.POST.get('raison', 'autre')
        details = request.POST.get('details', '').strip()[:500]
        Signalement.objects.create(
            annonce=annonce,
            auteur=request.user if request.user.is_authenticated else None,
            raison=raison,
            details=details,
        )
        messages.success(request, "Merci, votre signalement a été envoyé à l'équipe TBG.")
        return redirect(annonce.get_absolute_url())
    return render(request, 'ads/signaler.html', {'annonce': annonce})


# ── Admin stats dashboard ────────────────────────────────────────────────
@staff_required
def admin_stats(request):
    from django.utils import timezone as tz
    import datetime as dt
    today  = tz.now()
    last30 = today - dt.timedelta(days=30)

    annonces_par_jour = list(
        Annonce.objects
        .filter(created_at__gte=last30)
        .annotate(jour=TruncDay('created_at'))
        .values('jour')
        .annotate(count=Count('id'))
        .order_by('jour')
    )
    par_categorie = list(
        Annonce.objects.filter(statut='actif')
        .values('categorie')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    stats = {
        'total_actives':  Annonce.objects.filter(statut='actif').count(),
        'total_annonces': Annonce.objects.count(),
        'total_users':    User.objects.count(),
        'signalements':   Signalement.objects.count(),
        'aujourd_hui':    Annonce.objects.filter(created_at__date=today.date()).count(),
        'cette_semaine':  Annonce.objects.filter(created_at__gte=today - dt.timedelta(days=7)).count(),
    }
    cat_labels = dict(CATEGORIES)
    for c in par_categorie:
        c['label'] = cat_labels.get(c['categorie'], c['categorie'])
    max_day = max((d['count'] for d in annonces_par_jour), default=1)
    dernieres         = Annonce.objects.select_related('user', 'user__profil').order_by('-created_at')[:15]
    signalements_list = Signalement.objects.select_related('annonce', 'auteur').order_by('-created_at')[:10]
    return render(request, 'ads/admin_stats.html', {
        'stats':              stats,
        'annonces_par_jour':  annonces_par_jour,
        'par_categorie':      par_categorie,
        'max_day':            max_day,
        'dernieres':          dernieres,
        'signalements_list':  signalements_list,
    })


# ── Export CSV ───────────────────────────────────────────────────────────
@staff_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="tbg_annonces.csv"'
    response.write('\ufeff')  # BOM Excel UTF-8
    writer = csv.writer(response)
    writer.writerow(['ID', 'Titre', 'Catégorie', 'Prix (XPF)', 'Localisation',
                     'Vendeur', 'Email', 'Téléphone', 'Statut', 'Vues', 'Date'])
    for a in Annonce.objects.select_related('user', 'user__profil').order_by('-created_at'):
        writer.writerow([
            a.pk, a.titre, a.get_categorie_display(),
            a.prix, a.localisation,
            a.user.nom or '', a.user.email, a.user.tel or '',
            a.statut, a.views, a.created_at.strftime('%d/%m/%Y %H:%M'),
        ])
    return response


# ── Alertes annonces ──────────────────────────────────────────────────────
@login_required
def mes_alertes(request):
    from .models import AlerteAnnonce, CATEGORIES, SOUS_CATEGORIES
    alertes = AlerteAnnonce.objects.filter(user=request.user)
    return render(request, 'ads/mes_alertes.html', {
        'alertes': alertes,
        'categories': CATEGORIES,
        'sous_cats_data': _sous_cats_data(),
    })

@login_required
def creer_alerte(request):
    from .models import AlerteAnnonce
    if request.method == 'POST':
        cat = request.POST.get('categorie', '')
        sous_cat = request.POST.get('sous_categorie', '')
        if cat:
            AlerteAnnonce.objects.get_or_create(
                user=request.user,
                categorie=cat,
                sous_categorie=sous_cat,
            )
            messages.success(request, 'Alerte créée avec succès !')
    return redirect('mes_alertes')

@login_required
def supprimer_alerte(request, pk):
    from .models import AlerteAnnonce
    alerte = get_object_or_404(AlerteAnnonce, pk=pk, user=request.user)
    alerte.delete()
    messages.success(request, 'Alerte supprimée.')
    return redirect('mes_alertes')


# ── Custom 404 ───────────────────────────────────────────────────────────
def mentions_legales(request):
    return render(request, 'pages/mentions_legales.html')


def politique_confidentialite(request):
    return render(request, 'pages/politique_confidentialite.html')


def cgu(request):
    return render(request, 'ads/cgu.html')


def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Paiement Boost (PayZen embarqué)
# ═══════════════════════════════════════════════════════════════════════════════

BOOST_PRIX = {'7jours': 500, '1mois': 1500}


@login_required
def boost_from_edit(request, pk):
    """Initier un boost depuis la page de modification."""
    annonce = get_object_or_404(Annonce, pk=pk, user=request.user)

    # Si déjà boostée et pas expirée, ne pas permettre
    if annonce.boost_status == 'active' and annonce.boost_expires_at and annonce.boost_expires_at > timezone.now():
        messages.info(request, "Cette annonce est déjà boostée.")
        return redirect('edit_annonce', pk=pk)

    boost_duree = request.POST.get('boost_duree', '7jours')
    if boost_duree not in ('7jours', '1mois'):
        boost_duree = '7jours'

    annonce.boost_duree = boost_duree
    annonce.boost_status = 'pending'
    annonce.boost_payment_ref = f"BOOST{uuid.uuid4().hex[:8].upper()}"
    annonce.save(update_fields=['boost_duree', 'boost_status', 'boost_payment_ref'])

    request.session['boost_pending_pk'] = annonce.pk
    return redirect('boost_paiement', pk=annonce.pk)


@login_required
def boost_paiement(request, pk):
    """Affiche le formulaire de paiement embarqué pour le boost.

    Utilise exactement le même chemin de code que les pubs (create_embedded_form_token)
    via un objet adaptateur, pour garantir la compatibilité PayZen.
    """
    annonce = get_object_or_404(Annonce, pk=pk, user=request.user, boost_status='pending')

    if request.session.get('boost_pending_pk') != annonce.pk:
        messages.error(request, "Accès non autorisé.")
        return redirect(annonce.get_absolute_url())

    prix = BOOST_PRIX.get(annonce.boost_duree, 500)
    duree_label = '7 jours' if annonce.boost_duree == '7jours' else '1 mois'

    from pubs.payzen import create_embedded_form_token, build_payzen_form

    # Adaptateur : même interface que Publicite pour réutiliser create_embedded_form_token
    class _BoostAsPublicite:
        def __init__(self):
            self.prix = prix
            self.payment_ref = annonce.boost_payment_ref
            self.client_email = request.user.email
            self.client_nom = request.user.nom or request.user.email
            self.client_tel = ''

        def get_emplacement_display(self):
            return f"Boost {duree_label}"

        @property
        def duree_semaines(self):
            return 1 if annonce.boost_duree == '7jours' else 4

    boost_pub = _BoostAsPublicite()

    try:
        form_token, public_key = create_embedded_form_token(boost_pub, request, ipn_path='/boost/paiement/ipn/')
    except Exception as e:
        logger.exception("Boost: create_embedded_form_token failed: %s", e)
        # Fallback : redirection classique V2 si l'API REST échoue
        try:
            form_data, payment_url = build_payzen_form(
                boost_pub, request,
                return_path='/boost/paiement/succes/',
                ipn_path='/boost/paiement/ipn/',
            )
        except Exception as e2:
            logger.exception("Boost: V2 fallback also failed: %s", e2)
            messages.error(request, f"Erreur paiement : {e} | Fallback : {e2}")
            return redirect(annonce.get_absolute_url())

        return render(request, 'ads/boost_payzen_redirect.html', {
            'annonce': annonce,
            'prix': prix,
            'duree_label': duree_label,
            'form_data': form_data,
            'payment_url': payment_url,
        })

    return render(request, 'ads/paiement_boost.html', {
        'annonce': annonce,
        'prix': prix,
        'duree_label': duree_label,
        'form_token': form_token,
        'public_key': public_key,
    })


from django.views.decorators.csrf import csrf_exempt as _csrf_exempt


# @csrf_exempt requis : le SDK JS PayZen (Krypton) soumet ce formulaire
# via kr-post-url-success depuis le domaine PayZen — pas de cookie CSRF.
# Aucune action sensible ici (le boost est activé par l'IPN, pas par ce callback).
@_csrf_exempt
def boost_paiement_valide_js(request, pk):
    """Callback JS après paiement réussi côté client."""
    annonce = get_object_or_404(Annonce, pk=pk, user=request.user)
    # Le vrai traitement se fait via IPN. Ici on redirige.
    return JsonResponse({'redirect': f'/annonces/{pk}/'})


# @csrf_exempt requis : webhook PayZen (IPN) — appel serveur-à-serveur.
# Signatures HMAC-SHA-256 vérifiées ci-dessous (REST V4 et Formulaire V2).
@_csrf_exempt
def boost_ipn(request):
    """IPN PayZen pour le boost — gère API REST V4 et API Formulaire V2."""
    import json as _json
    from pubs.payzen import verify_rest_signature, verify_signature

    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    kr_answer = request.POST.get('kr-answer', '')
    kr_hash = request.POST.get('kr-hash', '')

    # ── Format REST V4 (formulaire embarqué) ──
    if kr_answer and kr_hash:
        if not verify_rest_signature(kr_answer, kr_hash):
            logger.warning("Boost IPN REST: invalid signature")
            return HttpResponse('Invalid signature', status=400)

        try:
            answer = _json.loads(kr_answer)
        except _json.JSONDecodeError:
            return HttpResponse('Invalid JSON', status=400)

        order_id = answer.get('orderDetails', {}).get('orderId', '')
        paid = answer.get('orderStatus', '') == 'PAID'

    # ── Format Formulaire V2 (redirection) ──
    elif request.POST.get('vads_order_id'):
        if not verify_signature(request.POST):
            logger.warning("Boost IPN V2: invalid signature")
            return HttpResponse('Invalid signature', status=400)

        order_id = request.POST.get('vads_order_id', '')
        result = request.POST.get('vads_result', '')
        status_v2 = request.POST.get('vads_trans_status', '')
        paid = result == '00' and status_v2 in ('AUTHORISED', 'CAPTURED')

    else:
        return HttpResponse('Missing data', status=400)

    try:
        annonce = Annonce.objects.get(boost_payment_ref=order_id)
    except Annonce.DoesNotExist:
        logger.warning("Boost IPN: order not found (ref=%s)", order_id)
        return HttpResponse('Order not found', status=404)

    if paid:
        annonce.boost = True
        annonce.boost_status = 'active'
        if annonce.boost_duree == '7jours':
            annonce.boost_expires_at = timezone.now() + datetime.timedelta(days=7)
        else:
            annonce.boost_expires_at = timezone.now() + datetime.timedelta(days=30)
        annonce.save()
        logger.info("Boost activé pour annonce #%s (ref=%s)", annonce.pk, order_id)
    else:
        annonce.boost_status = ''
        annonce.boost_duree = ''
        annonce.save()
        logger.warning("Boost paiement échoué pour annonce #%s (ref=%s)", annonce.pk, order_id)

    return HttpResponse('OK', status=200)


# @csrf_exempt requis : PayZen redirige le navigateur de l'acheteur via POST
# depuis son propre domaine (secure.osb.pf) — aucun cookie CSRF disponible.
# Cette vue ne fait qu'afficher un message et rediriger, aucune action sensible.
@_csrf_exempt
def boost_retour_succes(request):
    """Page de retour après paiement boost réussi (GET ou POST V2)."""
    pk = request.session.pop('boost_pending_pk', None)

    # Fallback V2 : retrouver l'annonce via vads_order_id
    if not pk and request.method == 'POST':
        order_id = request.POST.get('vads_order_id', '')
        if order_id:
            annonce = Annonce.objects.filter(boost_payment_ref=order_id).first()
            if annonce:
                pk = annonce.pk

    if pk:
        annonce = Annonce.objects.filter(pk=pk).first()
        if annonce:
            messages.success(request, f'Paiement accepté ! Votre boost est actif pour "{annonce.titre}".')
            return redirect(annonce.get_absolute_url())
    messages.success(request, "Paiement accepté ! Votre boost est actif.")
    return redirect('mes_annonces')


# @csrf_exempt requis : PayZen redirige le navigateur de l'acheteur via POST
# depuis son propre domaine (secure.osb.pf) — aucun cookie CSRF disponible.
# Cette vue ne fait qu'afficher un message et rediriger, aucune action sensible.
@_csrf_exempt
def boost_retour_echec(request):
    """Page de retour après paiement boost échoué (GET ou POST V2)."""
    pk = request.session.pop('boost_pending_pk', None)

    if not pk and request.method == 'POST':
        order_id = request.POST.get('vads_order_id', '')
        if order_id:
            annonce = Annonce.objects.filter(boost_payment_ref=order_id).first()
            if annonce:
                pk = annonce.pk

    if pk:
        annonce = Annonce.objects.filter(pk=pk).first()
        if annonce:
            messages.error(request, "Le paiement n'a pas abouti. Votre annonce est publiée sans boost.")
            return redirect(annonce.get_absolute_url())
    messages.error(request, "Le paiement n'a pas abouti.")
    return redirect('mes_annonces')


# ── Profil vendeur & notation ──────────────────────────────────────

from .models import Notation
from .notation_utils import peut_noter, note_moyenne, stats_vendeur, distribution_notes
from users.models import Profil


def profil_vendeur(request, user_id):
    """Page publique du profil vendeur avec avis et annonces."""
    vendeur = get_object_or_404(User, pk=user_id)

    # Récupérer ou créer le profil enrichi
    profil, _ = Profil.objects.get_or_create(user=vendeur)

    stats = stats_vendeur(vendeur)
    annonces = Annonce.objects.filter(user=vendeur, statut='actif').order_by('-created_at')
    notations = Notation.objects.filter(vendeur=vendeur).order_by('-date_creation').select_related('acheteur')[:20]

    distribution = distribution_notes(vendeur)
    # Prepare distribution list for template (5 to 1, with percentage)
    total_notes = stats['total_avis']
    distribution_list = []
    for i in range(5, 0, -1):
        count = distribution[i]
        pct = round(count * 100 / total_notes) if total_notes > 0 else 0
        distribution_list.append({'etoiles': i, 'count': count, 'pct': pct})

    peut_noter_vendeur = False
    if request.user.is_authenticated and request.user != vendeur:
        peut_noter_vendeur = peut_noter(request.user, vendeur)

    return render(request, 'ads/profil_vendeur.html', {
        'vendeur': vendeur,
        'profil': profil,
        'stats': stats,
        'annonces': annonces,
        'notations': notations,
        'peut_noter_vendeur': peut_noter_vendeur,
        'distribution_list': distribution_list,
    })


@login_required
def noter_vendeur(request, user_id):
    """API POST pour soumettre une notation."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Méthode non autorisée.'}, status=405)

    vendeur = get_object_or_404(User, pk=user_id)

    if request.user == vendeur:
        return JsonResponse({'success': False, 'message': 'Vous ne pouvez pas vous noter vous-même.'}, status=400)

    note_val = request.POST.get('note')
    avis_ecrit = request.POST.get('avis_ecrit', '').strip()

    if not note_val:
        return JsonResponse({'success': False, 'message': 'La note est requise.'}, status=400)

    try:
        note_val = int(note_val)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Note invalide.'}, status=400)

    if note_val < 1 or note_val > 5:
        return JsonResponse({'success': False, 'message': 'La note doit être entre 1 et 5.'}, status=400)

    if len(avis_ecrit) > 500:
        return JsonResponse({'success': False, 'message': 'L\'avis ne peut pas dépasser 500 caractères.'}, status=400)

    if not peut_noter(request.user, vendeur):
        return JsonResponse({'success': False, 'message': 'Vous avez déjà laissé un avis pour ce vendeur.'}, status=403)

    try:
        notation = Notation.objects.create(
            vendeur=vendeur,
            acheteur=request.user,
            note=note_val,
            avis_ecrit=avis_ecrit,
        )
    except Exception:
        return JsonResponse({'success': False, 'message': 'Vous avez déjà laissé un avis pour ce vendeur.'}, status=400)

    stats = note_moyenne(vendeur)

    # Construire le HTML du nouvel avis pour insertion dynamique
    from django.utils.dateformat import format as date_format
    date_str = date_format(notation.date_creation, 'd/m/Y')
    etoiles_html = ''
    for i in range(1, 6):
        color = '#f59e0b' if i <= notation.note else '#d1d5db'
        etoiles_html += f'<span style="color:{color}">★</span>'

    avis_html = f'''<div class="flex gap-3 pb-4 border-b border-gray-100">
        <div class="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-xs font-bold flex-shrink-0">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/></svg>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Utilisateur vérifié</span>
            <span class="text-amber-500 text-sm">{etoiles_html}</span>
            <span class="text-xs text-gray-400">{date_str}</span>
          </div>'''

    if avis_ecrit:
        from django.utils.html import escape
        avis_html += f'\n          <p class="text-sm text-gray-700 mt-1.5">{escape(avis_ecrit)}</p>'

    avis_html += '''
        </div>
      </div>'''

    return JsonResponse({
        'success': True,
        'message': 'Merci pour votre avis !',
        'nouvelle_moyenne': stats['moyenne'],
        'total_avis': stats['total_avis'],
        'avis_html': avis_html,
    })


# ── Import annonce depuis URL externe ─────────────────────────
import ipaddress
import socket
from urllib.parse import urlparse

import requests as http_requests
from bs4 import BeautifulSoup

_PRIVATE_NETS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
]


def _is_private_ip(hostname):
    """Retourne True si le hostname résout vers une IP privée."""
    try:
        addr = socket.getaddrinfo(hostname, None)[0][4][0]
        ip = ipaddress.ip_address(addr)
        return any(ip in net for net in _PRIVATE_NETS)
    except (socket.gaierror, ValueError):
        return True  # En cas de doute, bloquer


# Communes PF — noms exacts tels qu'utilisés dans le LocationSelector JS
# (commune_display, island_id) pour pouvoir pré-sélectionner côté frontend
_COMMUNES_PF = [
    ("Papeete", "tahiti"), ("Pirae", "tahiti"), ("Arue", "tahiti"),
    ("Mahina", "tahiti"), ("Papenoo", "tahiti"), ("Hitiaa O Te Ra", "tahiti"),
    ("Faaone", "tahiti"), ("Taiarapu-Est", "tahiti"), ("Taiarapu-Ouest", "tahiti"),
    ("Teva I Uta", "tahiti"), ("Papara", "tahiti"), ("Paea", "tahiti"),
    ("Punaauia", "tahiti"), ("Faa'a", "tahiti"),
    ("Afareaitu", "moorea"), ("Papeatoai", "moorea"), ("Haapiti", "moorea"),
    ("Pao Pao", "moorea"), ("Teavaro", "moorea"),
    ("Vaitape", "bora-bora"), ("Uturoa", "raiatea"),
    ("Fare", "huahine"), ("Rangiroa", "tuamotu"), ("Fakarava", "tuamotu"),
    ("Tikehau", "tuamotu"), ("Nuku Hiva", "marquises"), ("Hiva Oa", "marquises"),
    ("Rurutu", "australes"), ("Tubuai", "australes"),
]

# Alias courants → nom officiel LocationSelector
_COMMUNE_ALIASES = {
    'faaa': "Faa'a", 'faa a': "Faa'a", "faa'a": "Faa'a",
    'taravao': 'Taiarapu-Est', 'punaruu': 'Punaauia',
    'moorea': 'Afareaitu', 'bora bora': 'Vaitape', 'bora-bora': 'Vaitape',
    'raiatea': 'Uturoa', 'huahine': 'Fare',
    'paopao': 'Pao Pao', 'pao pao': 'Pao Pao',
    'mataiea': 'Teva I Uta', 'papeari': 'Teva I Uta',
    'hitiaa': 'Hitiaa O Te Ra', 'tiarei': 'Hitiaa O Te Ra',
}

# Sous-catégories immobilier — mots-clés → valeur
_SOUS_CAT_IMMO = [
    ('immo-appartements', ['appartement', 'studio', 'f1', 'f2', 'f3', 'f4', 'f5', 'duplex', 't1', 't2', 't3', 't4']),
    ('immo-maisons',      ['maison', 'villa', 'fare', 'bungalow', 'pavillon']),
    ('immo-terrains',     ['terrain', 'parcelle', 'lot', 'foncier']),
    ('immo-bureaux',      ['bureau', 'local commercial', 'commerce', 'entrepot', 'magasin', 'boutique']),
    ('immo-saisonnieres', ['saisonnier', 'saisonniere', 'vacance', 'meuble', 'courte duree', 'airbnb']),
    ('immo-parkings',     ['parking', 'garage', 'box', 'stationnement']),
]


def _extract_annonce_hints(titre, description):
    """Analyse titre + description pour deviner catégorie, transaction, prix, localisation."""
    import re
    result = {}
    text = f"{titre} {description}".lower()
    full_text = f"{titre} {description}"

    # ── Type de transaction ────────────────────────────────────────────
    location_kw = ['location', 'à louer', 'a louer', 'louer', 'loue', 'bail',
                   'mensuel', '/mois', 'par mois', 'charges comprises', 'loyer']
    vente_kw = ['vente', 'à vendre', 'a vendre', 'vends', 'vend', 'cession', 'prix de vente']

    loc_score = sum(1 for kw in location_kw if kw in text)
    vente_score = sum(1 for kw in vente_kw if kw in text)

    if loc_score > vente_score:
        result['type_transaction'] = 'location'
    elif vente_score > 0:
        result['type_transaction'] = 'vente'

    # ── Prix ───────────────────────────────────────────────────────────
    prix_patterns = [
        # "25 000 000 XPF" ou "25 000 000 F" ou "25.000.000 F"
        r'(\d[\d\s\.\,]{2,12}\d)\s*(?:XPF|FCFP|F\b|francs?)',
        # "25MF" ou "25 MF" ou "2.5MF"
        r'([\d]+(?:[.,]\d+)?)\s*(?:MF|millions?\s*(?:de\s*)?(?:XPF|F|francs?))',
        # "Prix : 25 000 000" ou "Loyer : 80 000"
        r'(?:prix|loyer|tarif|montant)\s*[:=]?\s*(\d[\d\s\.\,]{2,12}\d)',
        # Nombre isolé > 10000 suivi de XPF/F (format sans espaces)
        r'(\d{5,})\s*(?:XPF|FCFP|F\b)',
    ]

    prix = 0
    for pattern in prix_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
            try:
                val = float(raw)
                if 'MF' in match.group(0).upper() or 'million' in match.group(0).lower():
                    val *= 1_000_000
                prix = int(val)
                if prix > 0:
                    break
            except (ValueError, OverflowError):
                pass

    if prix > 0:
        result['prix'] = prix

    # ── Localisation ───────────────────────────────────────────────────
    # D'abord chercher les noms officiels
    for commune, island in _COMMUNES_PF:
        if commune.lower() in text:
            result['localisation'] = commune
            result['localisation_island'] = island
            break

    # Sinon chercher les alias
    if 'localisation' not in result:
        for alias, official in _COMMUNE_ALIASES.items():
            if alias in text:
                result['localisation'] = official
                # Trouver l'île correspondante
                for commune, island in _COMMUNES_PF:
                    if commune == official:
                        result['localisation_island'] = island
                        break
                break

    # ── Catégorie immobilier ───────────────────────────────────────────
    immo_kw = ['immobilier', 'appartement', 'maison', 'villa', 'terrain',
               'studio', 'duplex', 'f1', 'f2', 'f3', 'f4', 'f5',
               'chambre', 'lot', 'parcelle', 'bureau', 'local commercial',
               'location', 'loyer', 'à louer', 'a louer', 'à vendre', 'a vendre',
               'bungalow', 'fare', 'meublé', 'meuble']
    if sum(1 for kw in immo_kw if kw in text) >= 2:
        result['categorie'] = 'immobilier'

    # ── Sous-catégorie immobilier ──────────────────────────────────────
    if result.get('categorie') == 'immobilier':
        best_sc, best_score = '', 0
        for sc_value, keywords in _SOUS_CAT_IMMO:
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_sc = sc_value
        if best_sc:
            result['sous_categorie'] = best_sc

    return result


def _detect_source(url):
    host = urlparse(url).hostname or ''
    host = host.lower()
    if 'facebook.com' in host or 'fb.com' in host:
        return 'facebook'
    if 'pa.pf' in host:
        return 'papf'
    if 'leboncoin' in host:
        return 'leboncoin'
    if 'marketplace' in host:
        return 'marketplace'
    return 'autre'


@login_required
def import_url(request):
    """Scrape une URL externe et retourne titre/description/photo en JSON."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

    url = request.POST.get('url', '').strip()

    # Validation URL
    if not url:
        return JsonResponse({'success': False, 'error': 'Veuillez entrer une URL.'})

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return JsonResponse({'success': False, 'error': "L'URL doit commencer par http:// ou https://."})

    if not parsed.hostname:
        return JsonResponse({'success': False, 'error': 'URL invalide.'})

    # Bloquer IPs privées (SSRF)
    if _is_private_ip(parsed.hostname):
        return JsonResponse({'success': False, 'error': 'URL invalide.'})

    source = _detect_source(url)

    # Facebook bloque le scraping
    if source == 'facebook':
        return JsonResponse({
            'success': False,
            'error': "Facebook ne permet pas l'import automatique. Copiez-collez le titre et la description manuellement.",
        })

    # Requête HTTP
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.5',
    }

    try:
        resp = http_requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
    except http_requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'error': "Le site n'a pas répondu à temps (10s). Remplissez le formulaire manuellement."})
    except http_requests.exceptions.RequestException:
        return JsonResponse({'success': False, 'error': "Impossible d'accéder à ce lien. Vérifiez l'URL ou remplissez le formulaire manuellement."})

    # Parse HTML
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Extraire titre
    titre = ''
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content', '').strip():
        titre = og_title['content'].strip()
    elif soup.title and soup.title.string:
        titre = soup.title.string.strip()
    else:
        h1 = soup.find('h1')
        if h1:
            titre = h1.get_text(strip=True)

    # Extraire description
    description = ''
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content', '').strip():
        description = og_desc['content'].strip()
    else:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content', '').strip():
            description = meta_desc['content'].strip()
        else:
            # Premier paragraphe significatif
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 50:
                    description = text
                    break

    # Extraire photo
    photo_url = ''
    og_img = soup.find('meta', property='og:image')
    if og_img and og_img.get('content', '').strip():
        photo_url = og_img['content'].strip()
    else:
        for img in soup.find_all('img', src=True):
            src = img['src']
            # Ignorer logos, icônes (petites images)
            w = img.get('width', '')
            h = img.get('height', '')
            try:
                if w and int(w) < 100:
                    continue
                if h and int(h) < 100:
                    continue
            except (ValueError, TypeError):
                pass
            # Ignorer les data URIs très courts et les SVG
            if src.startswith('data:') or src.endswith('.svg'):
                continue
            # URL relative → absolue
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = f"{parsed.scheme}://{parsed.hostname}{src}"
            photo_url = src
            break

    # Décoder les entités HTML (&eacute; → é, &agrave; → à, etc.)
    import html as _html
    titre = _html.unescape(titre)
    description = _html.unescape(description)

    # Tronquer
    titre = titre[:200]
    description = description[:2000]

    # ── Extraction intelligente immobilier ─────────────────────────────
    detected = _extract_annonce_hints(titre, description)


    if not titre and not description:
        return JsonResponse({
            'success': False,
            'error': "Impossible d'extraire les informations de ce lien. Remplissez le formulaire manuellement.",
        })

    # Télécharger la photo côté serveur → base64 (évite les blocages CSP côté client)
    import base64
    photo_data = ''
    photo_mime = ''
    if photo_url:
        try:
            img_resp = http_requests.get(photo_url, headers=headers, timeout=8, stream=True)
            img_resp.raise_for_status()
            content_type = img_resp.headers.get('Content-Type', '')
            if content_type.startswith('image/') and int(img_resp.headers.get('Content-Length', 0) or 5_000_000) <= 5_000_000:
                img_bytes = img_resp.content
                if len(img_bytes) <= 5_000_000:
                    photo_data = base64.b64encode(img_bytes).decode('ascii')
                    photo_mime = content_type.split(';')[0]
        except Exception as e:
            logger.error("Erreur import photo depuis URL: %s", e)

    return JsonResponse({
        'success': True,
        'titre': titre,
        'description': description,
        'photo_url': photo_url,
        'photo_data': photo_data,
        'photo_mime': photo_mime,
        'source': source,
        **detected,
    })


# ─────────────────────────────────────────────────────────────────────
# Sync petites-annonces.pf — page admin
# ─────────────────────────────────────────────────────────────────────
@staff_required
def sync_pa_dashboard(request):
    """Tableau de bord de la sync petites-annonces.pf → TBG.

    GET  : affiche les options + 50 derniers runs
    POST : lance une sync avec les options choisies (synchrone, peut prendre 1-3 min)
    """
    from .models import PASyncRun
    from .scrapers.sync import sync_immobilier
    import threading

    if request.method == 'POST':
        cat   = request.POST.get('cat') or None
        limit = request.POST.get('limit') or None
        skip_photos = bool(request.POST.get('skip_photos'))

        try:
            cat_int   = int(cat)   if cat   else None
            limit_int = int(limit) if limit else None
        except ValueError:
            cat_int = None; limit_int = None

        # Lance en thread background pour ne pas bloquer le HTTP
        def _bg_sync():
            try:
                sync_immobilier(
                    limit=limit_int,
                    only_cat=cat_int,
                    skip_photos=skip_photos,
                    triggered_by=request.user,
                )
            except Exception as e:
                logger.exception(f'sync_pa_dashboard background error: {e}')

        threading.Thread(target=_bg_sync, daemon=True).start()
        messages.success(request, 'Sync lancée en arrière-plan. Recharge la page dans 1-3 minutes pour voir le résultat.')
        return redirect('sync_pa_dashboard')

    from users.models import User as UserModel
    runs = PASyncRun.objects.all()[:50]
    nb_imported = Annonce.objects.filter(is_imported=True).count()
    nb_imported_actives = Annonce.objects.filter(is_imported=True, statut='actif').count()
    nb_imported_archived = Annonce.objects.filter(is_imported=True, statut='expire').count()
    nb_users_imported = UserModel.objects.filter(is_imported=True).count()
    has_running = PASyncRun.objects.filter(status='running').exists()

    return render(request, 'ads/sync_pa_dashboard.html', {
        'runs': runs,
        'nb_imported': nb_imported,
        'nb_imported_actives': nb_imported_actives,
        'nb_imported_archived': nb_imported_archived,
        'nb_users_imported': nb_users_imported,
        'has_running': has_running,
        'CATEGORIES_PA': [
            (1, 'Vends appartement (immo-appartements / vente)'),
            (2, 'Vends maison (immo-maisons / vente)'),
            (3, 'Vends terrain (immo-terrains / vente)'),
            (4, 'Loue appartement (immo-appartements / location)'),
            (5, 'Loue maison (immo-maisons / location)'),
            (6, 'Saisonnière (immo-saisonnieres / location)'),
        ],
    })
