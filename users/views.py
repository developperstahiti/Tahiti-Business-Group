import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from ads.decorators import staff_required
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings as django_settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Sum, Q
from django.http import Http404, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import LoginForm, RegisterForm, ProfileForm
from ads.models import Annonce, Message, Notation
from ads.image_utils import save_webp
from forum.models import Sujet as ForumSujet

logger = logging.getLogger(__name__)

_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_SEC  = 15 * 60  # 15 minutes


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '0.0.0.0')


_url_validator = URLValidator(schemes=['http', 'https'])

def _clean_url(raw):
    """Valide et nettoie une URL de profil. Retourne '' si invalide."""
    raw = raw.strip()
    if not raw:
        return ''
    # Ajouter https:// si pas de scheme
    if not raw.startswith(('http://', 'https://')):
        raw = 'https://' + raw
    try:
        _url_validator(raw)
    except DjangoValidationError:
        return ''
    return raw


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    # Messages contextuels pour les redirections depuis la navbar
    _MSG_MAP = {
        'favoris':  "Connectez-vous pour enregistrer des annonces.",
        'messages': "Connectez-vous pour accéder à vos messages.",
    }
    msg_key = request.GET.get('msg', '')
    if msg_key in _MSG_MAP:
        messages.info(request, _MSG_MAP[msg_key])

    ip       = _client_ip(request)
    key      = f'login_fail_{ip}'
    attempts = cache.get(key, 0)

    # IP bloquée
    if attempts >= _LOGIN_MAX_ATTEMPTS:
        form = LoginForm()
        return render(request, 'users/login.html', {'form': form, 'locked': True})

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email    = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user     = authenticate(request, username=email, password=password)
        if user:
            cache.delete(key)          # Réinitialise le compteur en cas de succès
            login(request, user)
            messages.success(request, f"Bienvenue {user.nom or user.email} !")
            next_url = request.GET.get('next', 'index')
            if not url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_url = 'index'
            return redirect(next_url)
        else:
            attempts += 1
            cache.set(key, attempts, _LOGIN_LOCKOUT_SEC)
            remaining = _LOGIN_MAX_ATTEMPTS - attempts
            if remaining > 0:
                form.add_error(None, f"Email ou mot de passe incorrect. ({remaining} tentative{'s' if remaining > 1 else ''} restante{'s' if remaining > 1 else ''})")
            else:
                form.add_error(None, "Trop de tentatives échouées. Accès bloqué 15 minutes.")

    return render(request, 'users/login.html', {'form': form})


def _smtp_configured():
    return bool(getattr(django_settings, 'EMAIL_HOST_USER', ''))


def _send_verification_email(request, user):
    token = signing.dumps({'uid': user.pk}, salt='email-verify')
    link  = request.build_absolute_uri(f'/users/verify-email/{token}/')
    send_mail(
        subject='Confirmez votre adresse email — Tahiti Business Group',
        message=(
            f"Bonjour {user.nom or user.email},\n\n"
            f"Cliquez sur ce lien pour confirmer votre email :\n{link}\n\n"
            f"Ce lien expire dans 48 heures.\n\n— L'équipe TBG"
        ),
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    # Recupere ?ref=CODE pour pre-remplir le hidden field du formulaire
    ref_code = (request.GET.get('ref') or '').strip().upper()
    initial = {'ref': ref_code} if ref_code else {}

    form = RegisterForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        smtp_ok = _smtp_configured()
        if smtp_ok:
            user.email_verified = False
            user.is_active = False  # Inactif jusqu'à vérification
        user.save()
        if smtp_ok:
            _send_verification_email(request, user)
            messages.info(request, "Compte créé ! Vérifiez vos emails pour activer votre compte.")
            return redirect('login')
        else:
            login(request, user)
            messages.success(request, "Compte créé avec succès ! Bienvenue sur Tahiti Business Group.")
            # Email de bienvenue
            try:
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags

                html_msg = render_to_string('emails/bienvenue.html', {
                    'nom': user.nom or 'nouveau membre',
                })
                send_mail(
                    subject='Bienvenue sur Tahiti Business Group !',
                    message=strip_tags(html_msg),
                    from_email=None,  # uses DEFAULT_FROM_EMAIL
                    recipient_list=[user.email],
                    html_message=html_msg,
                    fail_silently=True,
                )
            except Exception as e:
                logger.error("Erreur envoi email bienvenue: %s", e)
            return redirect('index')

    return render(request, 'users/register.html', {'form': form})


def verify_email(request, token):
    try:
        data = signing.loads(token, salt='email-verify', max_age=48 * 3600)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(pk=data['uid'])
        user.email_verified = True
        user.is_active = True
        user.save(update_fields=['email_verified', 'is_active'])
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, "Email confirmé ! Bienvenue sur Tahiti Business Group.")
        return redirect('index')
    except (signing.BadSignature, signing.SignatureExpired, Exception):
        messages.error(request, "Lien de vérification invalide ou expiré.")
        return redirect('login')


def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('index')


@login_required
def mon_compte(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        avatar_file = request.FILES.get('avatar')
        if avatar_file:
            url = save_webp(avatar_file, 'avatars', f'user_{user.pk}', max_size=(400, 400))
            user.avatar_url = url
            user.avatar = None  # on n'utilise plus l'ImageField
        user.save()
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('mon_compte')

    annonces = Annonce.objects.filter(user=request.user).order_by('-created_at')
    messages_recus = Message.objects.filter(
        annonce__user=request.user
    ).select_related('annonce', 'from_user', 'to_user').order_by('-created_at')[:10]

    stats_agg = annonces.aggregate(
        total=Count('pk'),
        actives=Count('pk', filter=Q(statut='actif')),
        vendues=Count('pk', filter=Q(statut='vendu')),
        vues=Sum('views'),
    )
    stats = {
        'total': stats_agg['total'],
        'actives': stats_agg['actives'],
        'vendues': stats_agg['vendues'],
        'vues': stats_agg['vues'] or 0,
        'messages': messages_recus.count(),
    }

    forum_sujets = ForumSujet.objects.filter(auteur=request.user).order_by('-date_creation')[:5]

    return render(request, 'users/mon_compte.html', {
        'form': form,
        'annonces': annonces[:6],
        'messages_recus': messages_recus,
        'stats': stats,
        'forum_sujets': forum_sujets,
    })


@login_required
def upgrade_to_pro(request):
    if request.user.role != 'personnel':
        return redirect('mon_compte')
    if request.method == 'POST':
        nom_entreprise = request.POST.get('nom_entreprise', '').strip()
        if not nom_entreprise:
            messages.error(request, "Le nom d'entreprise est obligatoire.")
            return redirect('mon_compte')
        request.user.role = 'pro'
        request.user.nom_entreprise = nom_entreprise
        request.user.numero_tahiti = request.POST.get('numero_tahiti', '').strip()
        request.user.save(update_fields=['role', 'nom_entreprise', 'numero_tahiti'])
        messages.success(request, "Félicitations ! Votre compte est maintenant Professionnel.")
        return redirect('mon_compte')
    return redirect('mon_compte')


@staff_required
def admin_dashboard(request):

    from pubs.models import Publicite, DemandePublicite
    from .models import User

    SLOTS = [
        {'key': 'billboard',             'label': 'Billboard',                'desc': 'Plein écran en haut de page',   'prix': 100000, 'icon': '🖼'},
        {'key': 'sidebar_gauche',        'label': 'Sidebar Gauche',           'desc': 'Colonne gauche (sticky)',       'prix': 35000,  'icon': '◻'},
        {'key': 'sidebar_haut',          'label': 'Sidebar Droite — Haut',    'desc': 'Colonne droite – haut',        'prix': 40000,  'icon': '◻'},
        {'key': 'sidebar_milieu',        'label': 'Sidebar Droite — Milieu',  'desc': 'Colonne droite – milieu',      'prix': 28000,  'icon': '◻'},
        {'key': 'sidebar_bas',           'label': 'Sidebar Droite — Bas',     'desc': 'Colonne droite – bas',         'prix': 20000,  'icon': '◻'},
        {'key': 'strip_accueil_haut',    'label': 'Strip Accueil — Haut',     'desc': 'Page accueil – haut',          'prix': 8000,   'icon': '▬'},
        {'key': 'strip_accueil_milieu',  'label': 'Strip Accueil — Milieu',   'desc': 'Page accueil – milieu',        'prix': 8000,   'icon': '▬'},
        {'key': 'strip_accueil_bas',     'label': 'Strip Accueil — Bas',      'desc': 'Page accueil – bas',           'prix': 8000,   'icon': '▬'},
        {'key': 'strip_immo_haut',       'label': 'Strip Immobilier — Haut',  'desc': 'Page immobilier – haut',       'prix': 12000,  'icon': '▬'},
        {'key': 'strip_immo_milieu',     'label': 'Strip Immobilier — Milieu', 'desc': 'Page immobilier – milieu',    'prix': 10000,  'icon': '▬'},
        {'key': 'strip_immo_bas',        'label': 'Strip Immobilier — Bas',   'desc': 'Page immobilier – bas',        'prix': 8000,   'icon': '▬'},
        {'key': 'strip_vehicules_haut',  'label': 'Strip Véhicules — Haut',   'desc': 'Page véhicules – haut',       'prix': 12000,  'icon': '▬'},
        {'key': 'strip_vehicules_milieu','label': 'Strip Véhicules — Milieu',  'desc': 'Page véhicules – milieu',    'prix': 10000,  'icon': '▬'},
        {'key': 'strip_vehicules_bas',   'label': 'Strip Véhicules — Bas',    'desc': 'Page véhicules – bas',        'prix': 8000,   'icon': '▬'},
        {'key': 'strip_occasion_haut',   'label': 'Strip Occasion — Haut',    'desc': 'Page occasion – haut',        'prix': 12000,  'icon': '▬'},
        {'key': 'strip_occasion_milieu', 'label': 'Strip Occasion — Milieu',   'desc': 'Page occasion – milieu',     'prix': 10000,  'icon': '▬'},
        {'key': 'strip_occasion_bas',    'label': 'Strip Occasion — Bas',     'desc': 'Page occasion – bas',         'prix': 8000,   'icon': '▬'},
        {'key': 'strip_emploi_haut',     'label': 'Strip Emploi — Haut',      'desc': 'Page emploi – haut',          'prix': 12000,  'icon': '▬'},
        {'key': 'strip_emploi_milieu',   'label': 'Strip Emploi — Milieu',     'desc': 'Page emploi – milieu',       'prix': 10000,  'icon': '▬'},
        {'key': 'strip_emploi_bas',      'label': 'Strip Emploi — Bas',       'desc': 'Page emploi – bas',           'prix': 8000,   'icon': '▬'},
        {'key': 'strip_services_haut',   'label': 'Strip Services — Haut',    'desc': 'Page services – haut',        'prix': 12000,  'icon': '▬'},
        {'key': 'strip_services_milieu', 'label': 'Strip Services — Milieu',   'desc': 'Page services – milieu',     'prix': 10000,  'icon': '▬'},
        {'key': 'strip_services_bas',    'label': 'Strip Services — Bas',     'desc': 'Page services – bas',         'prix': 8000,   'icon': '▬'},
    ]

    # Associer chaque slot à sa pub active
    pubs_par_slot = {}
    for slot in SLOTS:
        pubs_par_slot[slot['key']] = Publicite.objects.filter(emplacement=slot['key']).first()

    slots_with_pub = []
    for slot in SLOTS:
        slots_with_pub.append({**slot, 'pub': pubs_par_slot.get(slot['key'])})

    stats = {
        'annonces_total':   Annonce.objects.count(),
        'annonces_actives': Annonce.objects.filter(statut='actif').count(),
        'annonces_moderees':Annonce.objects.filter(statut='modere').count(),
        'users_total':      User.objects.count(),
        'pubs_actives':     Publicite.objects.filter(actif=True).count(),
        'demandes_pubs':    DemandePublicite.objects.filter(traite=False).count(),
    }

    annonces_recentes = Annonce.objects.select_related('user').order_by('-created_at')[:20]
    demandes_pubs     = DemandePublicite.objects.filter(traite=False).order_by('-created_at')[:50]

    return render(request, 'users/admin_dashboard.html', {
        'stats':          stats,
        'slots':          slots_with_pub,
        'annonces_recentes': annonces_recentes,
        'demandes_pubs':  demandes_pubs,
    })


@login_required
def supprimer_compte(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if request.user.check_password(password):
            user = request.user
            # Suppression RGPD : anonymiser / supprimer les données liées
            Message.objects.filter(from_user=user).delete()
            Message.objects.filter(to_user=user).delete()
            Notation.objects.filter(acheteur=user).delete()
            Notation.objects.filter(vendeur=user).delete()
            Annonce.objects.filter(user=user).delete()
            # Déconnexion puis suppression du compte
            logout(request)
            user.delete()
            messages.success(request, "Votre compte et toutes vos données ont été supprimés définitivement.")
            return redirect('index')
        else:
            messages.error(request, "Mot de passe incorrect. Veuillez réessayer.")
    return render(request, 'users/supprimer_compte.html')


@staff_required
def test_email(request):
    """Diagnostic : teste l'envoi email — admin only."""
    backend = django_settings.EMAIL_BACKEND
    host_user = getattr(django_settings, 'EMAIL_HOST_USER', '(vide)')
    info = {
        'backend': backend,
        'host_user': host_user,
        'has_password': bool(getattr(django_settings, 'EMAIL_HOST_PASSWORD', '')),
        'timeout': getattr(django_settings, 'EMAIL_TIMEOUT', None),
    }
    try:
        result = send_mail(
            'Test Email TBG',
            'Si tu recois cet email, Brevo fonctionne correctement sur Railway.',
            django_settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        info['resultat'] = f'Envoye ({result})'
    except Exception as e:
        info['erreur'] = f'{type(e).__name__}: {e}'
    return JsonResponse(info)


@login_required
def parrainage(request):
    """Page parrainage : code, lien partage, invitations validees, recompenses."""
    user = request.user
    # Lien complet d'invitation
    base = 'https://www.tahitibusinessgroup.com'
    referral_link = f"{base}/users/register/?ref={user.referral_code}"

    # Tous les filleuls parraines par cet utilisateur
    filleuls_qs = user.referrals.all().order_by('-date_joined')
    total_filleuls = filleuls_qs.count()

    # Filleuls "valides" : ceux qui ont publie au moins 1 annonce
    filleuls_valides_ids = list(
        Annonce.objects.filter(user__in=filleuls_qs)
        .values_list('user_id', flat=True)
        .distinct()
    )
    nb_invitations_validees = len(filleuls_valides_ids)

    # Recompenses : 1 boost gratuit pour chaque tranche de 3 invitations validees
    nb_recompenses_meritees = nb_invitations_validees // 3
    nb_recompenses_actuelles = user.referral_rewards_earned
    nouvelles_recompenses = max(0, nb_recompenses_meritees - nb_recompenses_actuelles)
    if nouvelles_recompenses > 0:
        user.referral_rewards_earned = nb_recompenses_meritees
        user.save(update_fields=['referral_rewards_earned'])

    # Progression vers la prochaine recompense (sur 3)
    progression = nb_invitations_validees % 3
    restants = 3 - progression if progression < 3 else 0

    # Liste des derniers filleuls (sans email visible)
    derniers_filleuls = []
    valides_set = set(filleuls_valides_ids)
    for f in filleuls_qs[:10]:
        prenom = (f.nom or 'Membre').split()[0] if f.nom else 'Membre'
        derniers_filleuls.append({
            'prenom': prenom,
            'date_joined': f.date_joined,
            'valide': f.pk in valides_set,
        })

    # Texte WhatsApp pre-rempli
    msg_partage = (
        f"Salut ! Inscris-toi sur Tahiti Business Group avec mon code de parrainage : "
        f"{referral_link}"
    )

    return render(request, 'users/parrainage.html', {
        'referral_code': user.referral_code,
        'referral_link': referral_link,
        'total_filleuls': total_filleuls,
        'nb_invitations_validees': nb_invitations_validees,
        'nb_recompenses_meritees': nb_recompenses_meritees,
        'recompenses_range': range(1, nb_recompenses_meritees + 1),
        'progression': progression,
        'restants': restants,
        'derniers_filleuls': derniers_filleuls,
        'msg_partage': msg_partage,
    })


@login_required
def modifier_profil(request):
    from .models import Profil
    profil, _ = Profil.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Champs texte
        profil.bio = request.POST.get('bio', '')[:500]
        profil.localisation = request.POST.get('localisation', '')[:100]
        profil.whatsapp = request.POST.get('whatsapp', '')[:20]
        profil.facebook_url = _clean_url(request.POST.get('facebook_url', ''))
        profil.instagram_url = _clean_url(request.POST.get('instagram_url', ''))
        profil.site_web = _clean_url(request.POST.get('site_web', ''))

        # Photo de profil (max 2 Mo) → S3 persistant
        if 'photo_profil' in request.FILES:
            photo = request.FILES['photo_profil']
            if photo.size <= 2 * 1024 * 1024:
                from ads.image_utils import save_webp
                profil.photo_profil_url = save_webp(
                    photo, 'profils/photos', f'profil_{request.user.pk}',
                    max_size=(400, 400),
                )

        # Image de fond (max 5 Mo) → S3 persistant
        if 'image_fond' in request.FILES:
            img = request.FILES['image_fond']
            if img.size <= 5 * 1024 * 1024:
                from ads.image_utils import save_webp
                profil.image_fond_url = save_webp(
                    img, 'profils/bannieres', f'banner_{request.user.pk}',
                    max_size=(1400, 400),
                )

        profil.save()
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('modifier_profil')

    return render(request, 'users/modifier_profil.html', {'profil': profil})


@staff_required
def moderer_annonce(request, pk):
    annonce = get_object_or_404(Annonce, pk=pk)
    action = request.POST.get('action')
    if action == 'approuver':
        annonce.statut = 'actif'
    elif action == 'moderer':
        annonce.statut = 'modere'
    elif action == 'supprimer':
        annonce.delete()
        messages.success(request, "Annonce supprimée.")
        return redirect('admin_dashboard')
    annonce.save()
    messages.success(request, f"Annonce {action}e.")
    return redirect('admin_dashboard')