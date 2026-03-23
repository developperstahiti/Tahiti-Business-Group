import os
import re
import uuid
import datetime
import csv
import logging
from django.conf import settings as django_settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models as db_models
from django.db.models import Q, Case, When, Value, IntegerField, Count
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from .models import Annonce, Message, CATEGORIES, SOUS_CATEGORIES, Signalement, PRIX_UNITE_CHOICES
from .image_utils import save_webp
from rubriques.models import ArticlePromo, ArticleInfo, ArticleNouveaute

User = get_user_model()
logger = logging.getLogger(__name__)


def _save_webp(file_obj, user_pk):
    return save_webp(file_obj, 'annonces', str(user_pk), max_size=(900, 700))


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


def _sous_cats_data():
    return {
        cat: [{'value': v, 'label': l} for v, l in items]
        for cat, items in SOUS_CATEGORIES.items()
    }



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
    ).order_by('-_boost_rank', '-created_at')


def index(request):
    base = Annonce.objects.filter(statut='actif').select_related('user')
    qs = _apply_boost_sort(base)
    annonces_recentes = qs[:10]
    total_count = base.count()

    # Ordre d'affichage : immobilier, véhicules, occasion, puis le reste
    cat_order = ['immobilier', 'vehicules', 'occasion'] + [
        code for code, _ in CATEGORIES if code not in ('immobilier', 'vehicules', 'occasion')
    ]
    cat_labels = dict(CATEGORIES)
    annonces_par_cat = []
    for code in cat_order:
        cat_qs = _apply_boost_sort(
            Annonce.objects.filter(statut='actif', categorie=code).select_related('user')
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


def liste_annonces(request):
    qs = Annonce.objects.filter(statut='actif').select_related('user')
    q        = request.GET.get('q', '')
    cat      = request.GET.get('categorie', '')
    sous_cat = request.GET.get('sous_cat', '')
    ville    = request.GET.get('localisation', '')
    prix_min = request.GET.get('prix_min', '')
    prix_max = request.GET.get('prix_max', '')
    tri      = request.GET.get('tri', '')

    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(description__icontains=q))
    if cat:
        qs = qs.filter(categorie=cat)
    if sous_cat:
        qs = qs.filter(sous_categorie=sous_cat)
    if ville:
        qs = qs.filter(localisation__icontains=ville)
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

    if tri == 'prix_asc':
        qs = qs.order_by('prix')
    elif tri == 'prix_desc':
        qs = qs.order_by('-prix')
    elif tri == 'recent':
        qs = qs.order_by('-created_at')
    else:
        qs = _apply_boost_sort(qs)

    # Sous-catégories disponibles pour la catégorie active
    sous_cats_dispo = SOUS_CATEGORIES.get(cat, []) if cat else []

    paginator = Paginator(qs, 24)
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
    })


def annonce_detail(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk, statut='actif')
    annonce.increment_views()

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
            return redirect('annonce_detail', pk=pk)

    annonces_similaires = Annonce.objects.filter(
        statut='actif', categorie=annonce.categorie
    ).exclude(pk=pk).select_related('user')[:4]

    return render(request, 'ads/detail.html', {
        'annonce':             annonce,
        'annonces_similaires': annonces_similaires,
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
            annonce.specs = _clean_specs(request.POST)
            photos = []
            for f in request.FILES.getlist('photos')[:5]:
                try:
                    url = _save_webp(f, request.user.pk)
                    logger.info("Photo sauvegardée OK: %s", url)
                    photos.append(url)
                except Exception as e:
                    logger.error("Erreur upload photo annonce: %s", e, exc_info=True)
            logger.info("=== PHOTOS FINAL: %d photo(s) => %s", len(photos), photos)
            annonce.photos = photos

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
                except Exception:
                    pass

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
                })
                send_mail(
                    subject=f'Votre annonce "{annonce.titre}" est en ligne sur TBG',
                    message=strip_tags(html_msg),
                    from_email=None,
                    recipient_list=[request.user.email],
                    html_message=html_msg,
                    fail_silently=True,
                )
            except Exception:
                pass

            if boost_duree in ('7jours', '1mois'):
                messages.success(request, "Annonce publiée ! Votre demande de boost a bien été envoyée — notre équipe vous contactera pour le paiement.")
            else:
                messages.success(request, f"Annonce publiée ! {len(photos)} photo(s) ajoutée(s).")
            return redirect('annonce_detail', pk=annonce.pk)
    else:
        form = AnnonceForm()

    return render(request, 'ads/deposer.html', {
        'form':               form,
        'sous_categories_data': _sous_cats_data(),
    })


@login_required
def mes_annonces(request):
    qs = Annonce.objects.filter(user=request.user)
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
        annonce.localisation   = request.POST.get('localisation', '').strip() or annonce.localisation
        annonce.prix_label     = request.POST.get('prix_label', '').strip()
        annonce.prix_unite     = request.POST.get('prix_unite', '')
        try:
            annonce.prix = int(request.POST.get('prix', 0) or 0)
        except (ValueError, TypeError):
            annonce.prix = 0

        # Supprimer les photos cochées
        to_delete = request.POST.getlist('delete_photos')
        current   = [p for p in annonce.photos if p not in to_delete]
        for url in to_delete:
            try:
                rel  = url.replace(django_settings.MEDIA_URL, '')
                path = os.path.join(django_settings.MEDIA_ROOT, rel)
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        # Réordonner les photos existantes selon l'ordre envoyé
        photo_order = request.POST.getlist('photo_order')
        if photo_order:
            ordered = [url for url in photo_order if url in current]
            # Ajouter les photos pas dans l'ordre (sécurité)
            for url in current:
                if url not in ordered:
                    ordered.append(url)
            current = ordered

        # Ajouter nouvelles photos (max 5 total)
        for photo_file in request.FILES.getlist('photos'):
            if len(current) >= 5:
                break
            try:
                current.append(_save_webp(photo_file, request.user.pk))
            except Exception:
                pass

        annonce.photos = current
        annonce.save()
        messages.success(request, "Annonce modifiée avec succès.")
        return redirect('annonce_detail', pk=annonce.pk)

    return render(request, 'ads/edit_annonce.html', {
        'annonce':              annonce,
        'categories':           CATEGORIES,
        'prix_unite_choices':   PRIX_UNITE_CHOICES,
        'sous_categories_data': _sous_cats_data(),
        'remaining_slots':      max(0, 5 - len(annonce.photos)),
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
            except Exception:
                pass
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
def contact_annonce(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk)
    User = get_user_model()

    # Le vendeur peut voir ses conversations avec les acheteurs via ?with=<pk>
    if annonce.user == request.user:
        other_pk = request.GET.get('with')
        if not other_pk:
            return JsonResponse({'error': 'Paramètre manquant'}, status=400)
        buyer = get_object_or_404(User, pk=other_pk)
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
        if not content:
            return JsonResponse({'error': 'Message vide'}, status=400)
        to_user = buyer if request.user == seller else seller
        msg = Message.objects.create(
            annonce=annonce,
            from_user=request.user,
            to_user=to_user,
            content=content,
        )
        # Email notification au vendeur
        try:
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags

            html_msg = render_to_string('emails/nouveau_message.html', {
                'vendeur_nom': annonce.user.nom or 'vendeur',
                'annonce_titre': annonce.titre,
                'acheteur_nom': msg.from_user.nom or msg.from_user.email,
                'message_preview': msg.content[:60] + ('...' if len(msg.content) > 60 else ''),
            })
            send_mail(
                subject=f'Nouveau message pour votre annonce "{annonce.titre}" — TBG',
                message=strip_tags(html_msg),
                from_email=None,
                recipient_list=[annonce.user.email],
                html_message=html_msg,
                fail_silently=True,
            )
        except Exception:
            pass
        thread.filter(from_user=to_user, read=False).update(read=True)
        html = render_to_string(
            'partials/_message_bubble.html',
            {'msg': msg, 'me': request.user},
            request=request,
        )
        return JsonResponse({'success': True, 'html': html})

    # GET → mark received messages as read, return modal HTML
    thread.filter(to_user=request.user, read=False).update(read=True)
    with_pk = request.GET.get('with')
    html = render_to_string(
        'ads/contact_modal.html',
        {'annonce': annonce, 'thread': thread, 'with_pk': with_pk},
        request=request,
    )
    return JsonResponse({'html': html})


@login_required
def mes_messages(request):
    all_msgs = Message.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).select_related('annonce', 'from_user', 'to_user').order_by('-created_at')

    # One conversation entry per annonce
    seen = set()
    conversations = []
    for msg in all_msgs:
        if msg.annonce_id not in seen:
            seen.add(msg.annonce_id)
            other = msg.to_user if msg.from_user == request.user else msg.from_user
            unread = Message.objects.filter(
                annonce=msg.annonce, to_user=request.user, read=False
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


# ── Mes Favoris ──────────────────────────────────────────────────────────
def mes_favoris(request):
    ids_raw = request.GET.get('ids', '')
    annonces = []
    if ids_raw:
        try:
            pk_list = [int(x.strip()) for x in ids_raw.split(',') if x.strip().isdigit()][:50]
            annonces = list(Annonce.objects.filter(pk__in=pk_list, statut='actif').select_related('user'))
        except (ValueError, TypeError):
            pass
    return render(request, 'ads/mes_favoris.html', {'annonces': annonces})


# ── Signaler une annonce ─────────────────────────────────────────────────
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
        return redirect('annonce_detail', pk=pk)
    return render(request, 'ads/signaler.html', {'annonce': annonce})


# ── Admin stats dashboard ────────────────────────────────────────────────
@login_required
def admin_stats(request):
    if not request.user.is_staff:
        from django.http import Http404
        raise Http404
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
    dernieres         = Annonce.objects.select_related('user').order_by('-created_at')[:15]
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
@login_required
def export_csv(request):
    if not request.user.is_staff:
        from django.http import Http404
        raise Http404
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="tbg_annonces.csv"'
    response.write('\ufeff')  # BOM Excel UTF-8
    writer = csv.writer(response)
    writer.writerow(['ID', 'Titre', 'Catégorie', 'Prix (XPF)', 'Localisation',
                     'Vendeur', 'Email', 'Téléphone', 'Statut', 'Vues', 'Date'])
    for a in Annonce.objects.select_related('user').order_by('-created_at'):
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
    return render(request, 'ads/mentions_legales.html')


def cgu(request):
    return render(request, 'ads/cgu.html')


def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


# ── Sitemap dynamique ─────────────────────────────────────────────────────
def sitemap_xml(request):
    base = request.build_absolute_uri('/').rstrip('/')
    annonces = Annonce.objects.filter(statut='actif').values('pk', 'updated_at').order_by('-updated_at')[:50000]
    categories_sitemap = [
        {'code': code, 'label': label}
        for code, label in CATEGORIES
    ]
    static_pages = [
        {'path': '/pubs/tarifs/', 'changefreq': 'monthly', 'priority': '0.6'},
        {'path': '/info/', 'changefreq': 'weekly', 'priority': '0.7'},
        {'path': '/business/', 'changefreq': 'weekly', 'priority': '0.7'},
    ]
    today = datetime.date.today().isoformat()
    xml = render_to_string('sitemap.xml', {
        'base': base,
        'annonces': annonces,
        'categories_sitemap': categories_sitemap,
        'static_pages': static_pages,
        'today': today,
    }, request=request)
    return HttpResponse(xml, content_type='application/xml')
