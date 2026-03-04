import io
import os
import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone
from django.conf import settings as django_settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from PIL import Image as PILImage
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import get_user_model
from django.db.models.functions import TruncDay
from django.db.models import Count
import datetime
import csv
from .models import Annonce, Message, CATEGORIES, SOUS_CATEGORIES, Signalement
from rubriques.models import ArticlePromo, ArticleInfo, ArticleNouveaute
User = get_user_model()


def _save_webp(file_obj, user_pk):
    img = PILImage.open(file_obj)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail((900, 700), PILImage.LANCZOS)

    if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
        import boto3
        bucket = os.environ['AWS_STORAGE_BUCKET_NAME']
        region = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')
        key = f"annonces/{user_pk}_{uuid.uuid4().hex[:8]}.webp"
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=85, method=6)
        buf.seek(0)
        boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        ).put_object(Bucket=bucket, Key=key, Body=buf, ContentType='image/webp')
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

    # Fallback local (développement sans S3)
    upload_dir = os.path.join(django_settings.MEDIA_ROOT, 'annonces')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{user_pk}_{uuid.uuid4().hex[:8]}.webp"
    filepath = os.path.join(upload_dir, filename)
    img.save(filepath, format='WEBP', quality=85, method=6)
    return f"{django_settings.MEDIA_URL}annonces/{filename}"


def _sous_cats_json():
    return json.dumps(
        {cat: [{'value': v, 'label': l} for v, l in items]
         for cat, items in SOUS_CATEGORIES.items()},
        ensure_ascii=False
    )



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

    annonces_par_cat = {}
    for code, label in CATEGORIES:
        cat_qs = _apply_boost_sort(
            Annonce.objects.filter(statut='actif', categorie=code).select_related('user')
        )
        annonces_par_cat[code] = {
            'label': label,
            'annonces': list(cat_qs[:10]),
        }

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
    prix_max = request.GET.get('prix_max', '')

    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(description__icontains=q))
    if cat:
        qs = qs.filter(categorie=cat)
    if sous_cat:
        qs = qs.filter(sous_categorie=sous_cat)
    if ville:
        qs = qs.filter(localisation__icontains=ville)
    if prix_max:
        try:
            qs = qs.filter(prix__lte=int(prix_max))
        except ValueError:
            pass

    qs = _apply_boost_sort(qs)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'ads/liste.html', {
        'annonces':   page,
        'categories': CATEGORIES,
        'q':          q,
        'cat_active': cat,
        'sous_cat':   sous_cat,
        'ville':      ville,
        'prix_max':   prix_max,
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
    # L'utilisateur a-t-il déjà utilisé son boost gratuit ?
    can_free_boost = True
    if request.user.is_authenticated:
        can_free_boost = not request.user.annonces.filter(boost_duree='1jour').exists()

    if request.method == 'POST':
        if _rate_limited(request, 'deposer', max_count=5, period_minutes=60):
            messages.error(request, "Limite atteinte : 5 annonces par heure maximum. Réessayez plus tard.")
            return redirect('deposer_annonce')
        form = AnnonceForm(request.POST, request.FILES)
        if form.is_valid():
            annonce = form.save(commit=False)
            annonce.user = request.user
            annonce.sous_categorie = request.POST.get('sous_categorie', '')
            specs = {k[5:]: v.strip() for k, v in request.POST.items()
                     if k.startswith('spec_') and v.strip()}
            annonce.specs = specs
            photos = []
            for f in request.FILES.getlist('photos')[:5]:
                try:
                    photos.append(_save_webp(f, request.user.pk))
                except Exception:
                    pass
            annonce.photos = photos

            # ── Boost ──────────────────────────────────────────────────────
            boost_duree   = request.POST.get('boost_duree', '').strip()
            boost_demande = request.POST.get('boost_demande', '').strip()

            if boost_duree == '1jour':
                if can_free_boost:
                    annonce.boost            = True
                    annonce.boost_duree      = '1jour'
                    annonce.boost_status     = 'active'
                    annonce.boost_expires_at = timezone.now() + datetime.timedelta(days=1)
                else:
                    messages.warning(request, "Boost gratuit déjà utilisé — annonce publiée sans boost.")
            elif boost_duree == '7jours':
                annonce.boost_duree    = '7jours'
                annonce.boost_status   = 'pending'
                annonce.boost_demande  = boost_demande
            elif boost_duree == '1mois':
                annonce.boost_duree    = '1mois'
                annonce.boost_status   = 'pending'
                annonce.boost_demande  = boost_demande

            annonce.save()
            if boost_duree in ('7jours', '1mois'):
                messages.success(request, "Annonce publiée ! Votre demande de boost a bien été envoyée — notre équipe vous contactera pour le paiement.")
            elif boost_duree == '1jour' and can_free_boost:
                messages.success(request, f"Annonce publiée et boostée 24h ! {len(photos)} photo(s) ajoutée(s).")
            else:
                messages.success(request, f"Annonce publiée ! {len(photos)} photo(s) ajoutée(s).")
            return redirect('annonce_detail', pk=annonce.pk)
    else:
        form = AnnonceForm()

    return render(request, 'ads/deposer.html', {
        'form':                 form,
        'sous_categories_json': _sous_cats_json(),
        'can_free_boost':       can_free_boost,
    })


@login_required
def mes_annonces(request):
    annonces = Annonce.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'ads/mes_annonces.html', {'annonces': annonces})


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
        new_specs = {k[5:]: v.strip() for k, v in request.POST.items()
                     if k.startswith('spec_') and v.strip()}
        if new_specs:
            annonce.specs = new_specs
        annonce.localisation   = request.POST.get('localisation', '').strip() or annonce.localisation
        annonce.prix_label     = request.POST.get('prix_label', '').strip()
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
        return redirect('mes_annonces')

    return render(request, 'ads/edit_annonce.html', {
        'annonce':              annonce,
        'categories':           CATEGORIES,
        'sous_categories_json': _sous_cats_json(),
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


# ── Custom 404 ───────────────────────────────────────────────────────────
def custom_404(request, exception=None):
    return render(request, '404.html', status=404)
