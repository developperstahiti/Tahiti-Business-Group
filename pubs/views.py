import json
import logging
import uuid
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Publicite, DemandePublicite,
    PRIX_PAR_EMPLACEMENT, DISCOUNT_PAR_DUREE, calculer_prix,
)
from .forms import PubliciteForm, DemandePubliciteForm, DepotPubliciteForm
from .payzen import (
    build_payzen_form, verify_signature,
    create_embedded_form_token, verify_rest_signature,
)

logger = logging.getLogger(__name__)


def _staff_required(request):
    """Retourne True si l'accès est autorisé, sinon redirige."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Admin CRUD (inchangé)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def pub_creer(request):
    if not _staff_required(request):
        return redirect('index')
    emplacement = request.GET.get('emplacement', '')
    initial = {'emplacement': emplacement} if emplacement else {}
    form = PubliciteForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Publicité créée avec succès.")
        return redirect('admin_dashboard')
    return render(request, 'pubs/pub_form.html', {'form': form, 'action': 'Créer'})


@login_required
def pub_modifier(request, pk):
    if not _staff_required(request):
        return redirect('index')
    pub = get_object_or_404(Publicite, pk=pk)
    form = PubliciteForm(request.POST or None, request.FILES or None, instance=pub)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Publicité modifiée avec succès.")
        return redirect('admin_dashboard')
    return render(request, 'pubs/pub_form.html', {'form': form, 'pub': pub, 'action': 'Modifier'})


@login_required
def pub_supprimer(request, pk):
    if not _staff_required(request):
        return redirect('index')
    pub = get_object_or_404(Publicite, pk=pk)
    if request.method == 'POST':
        if pub.image:
            pub.image.delete(save=False)
        pub.titre        = 'Emplacement disponible'
        pub.description  = ''
        pub.image_url    = ''
        pub.lien         = ''
        pub.actif        = False
        pub.client_nom   = ''
        pub.client_email = ''
        pub.client_tel   = ''
        pub.date_debut   = None
        pub.date_fin     = None
        pub.payment_status = 'none'
        pub.save()
        messages.success(request, "Slot libéré — l'emplacement est à nouveau disponible à la réservation.")
    return redirect('admin_dashboard')


@login_required
def pub_toggle(request, pk):
    if not _staff_required(request):
        return redirect('index')
    pub = get_object_or_404(Publicite, pk=pk)
    if request.method == 'POST':
        pub.actif = not pub.actif
        pub.save()
    return redirect('admin_dashboard')


# ═══════════════════════════════════════════════════════════════════════════════
# Pages publiques (tarifs, demande manuelle)
# ═══════════════════════════════════════════════════════════════════════════════

def tarifs_pubs(request):
    pubs_haut   = Publicite.objects.filter(emplacement='haut', actif=True).first()
    pubs_milieu = Publicite.objects.filter(emplacement='milieu', actif=True).first()
    pubs_bas    = Publicite.objects.filter(emplacement='bas', actif=True).first()

    return render(request, 'pubs/tarifs.html', {
        'pubs_haut':   pubs_haut,
        'pubs_milieu': pubs_milieu,
        'pubs_bas':    pubs_bas,
        'tarifs': [
            {'emplacement': 'Haut de sidebar', 'prix': 40000, 'desc': 'Meilleure visibilité, premier regard', 'slug': 'haut'},
            {'emplacement': 'Milieu de sidebar', 'prix': 28000, 'desc': 'Position centrale, très efficace', 'slug': 'milieu'},
            {'emplacement': 'Bas de sidebar', 'prix': 20000, 'desc': 'Présence permanente, tarif abordable', 'slug': 'bas'},
        ],
    })


def demande_pub(request):
    form = DemandePubliciteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Votre demande a été envoyée ! Nous vous contacterons sous 24h.")
        return redirect('tarifs_pubs')
    return render(request, 'pubs/demande.html', {'form': form})


# ═══════════════════════════════════════════════════════════════════════════════
# Self-service : Déposer une pub + payer via PayZen
# ═══════════════════════════════════════════════════════════════════════════════

def deposer_pub(request):
    """Formulaire public pour déposer et payer une publicité."""
    emplacement_pre = request.GET.get('emplacement', '')
    initial = {}
    if emplacement_pre:
        initial['emplacement'] = emplacement_pre

    form = DepotPubliciteForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        duree = int(cd['duree'])
        prix_total = calculer_prix(cd['emplacement'], duree)

        image_file = cd.get('image')
        image_url = cd.get('image_url', '').strip()

        # Vérifier qu'au moins une source d'image est fournie
        if not image_file and not image_url:
            form.add_error(None, "Veuillez uploader une image ou coller un lien d'image.")
        else:
            # Créer la pub en attente de paiement
            pub = Publicite(
                titre=cd['titre'],
                image=image_file if image_file else None,
                image_url=image_url if not image_file else '',
                lien=cd['lien'],
                emplacement=cd['emplacement'],
                prix=prix_total,
                actif=False,
                client_nom=cd['client_nom'],
                client_email=cd['client_email'],
                client_tel=cd.get('client_tel', ''),
                duree_semaines=duree,
                payment_status='pending',
                payment_ref=f"TBG{uuid.uuid4().hex[:8].upper()}",
            )
            pub.save()

            # Stocker l'ID en session pour vérification
            request.session['pub_pending_pk'] = pub.pk
            return redirect('initier_paiement', pk=pub.pk)

    # Données de prix pour le JS
    prix_json = json.dumps(PRIX_PAR_EMPLACEMENT)
    discount_json = json.dumps(DISCOUNT_PAR_DUREE)

    return render(request, 'pubs/deposer.html', {
        'form': form,
        'prix_json': prix_json,
        'discount_json': discount_json,
    })


def initier_paiement(request, pk):
    """Affiche le formulaire de paiement embarqué PayZen."""
    pub = get_object_or_404(Publicite, pk=pk, payment_status='pending')

    # Vérifier que c'est bien l'utilisateur qui a créé cette pub
    if request.session.get('pub_pending_pk') != pub.pk:
        messages.error(request, "Accès non autorisé.")
        return redirect('deposer_pub')

    try:
        form_token, public_key = create_embedded_form_token(pub, request)
    except RuntimeError:
        # Fallback : redirection classique si l'API REST échoue
        logger.exception("Embedded form token creation failed, falling back to redirect")
        form_data, payment_url = build_payzen_form(pub, request)
        return render(request, 'pubs/payzen_redirect.html', {
            'form_data':   form_data,
            'payment_url': payment_url,
            'pub':         pub,
        })

    return render(request, 'pubs/paiement_embarque.html', {
        'pub':        pub,
        'form_token': form_token,
        'public_key': public_key,
    })


@csrf_exempt
def retour_paiement(request):
    """Page de retour après paiement (navigateur de l'acheteur).

    Gère les retours de l'API Formulaire (vads_*) et de l'API REST (succes/echec URLs).
    """
    data = request.POST if request.method == 'POST' else request.GET

    # Retour API Formulaire (redirection)
    order_id = data.get('vads_order_id', '')
    result   = data.get('vads_result', '')
    status   = data.get('vads_trans_status', '')

    pub = None

    if order_id:
        success = (result == '00' and status in ('AUTHORISED', 'CAPTURED'))
        pub = Publicite.objects.filter(payment_ref=order_id).first()
    else:
        # Retour formulaire embarqué : détecter via l'URL
        path = request.path
        if 'succes' in path:
            success = True
            # Récupérer la pub depuis la session
            pk = request.session.get('pub_pending_pk')
            if pk:
                pub = Publicite.objects.filter(pk=pk, payment_status='paid').first()
        elif 'echec' in path:
            success = False
            pk = request.session.get('pub_pending_pk')
            if pk:
                pub = Publicite.objects.filter(pk=pk).first()
        else:
            success = False

    return render(request, 'pubs/paiement_resultat.html', {
        'success': success,
        'pub':     pub,
    })


@csrf_exempt
def ipn_paiement(request):
    """IPN (Instant Payment Notification) — appel serveur-à-serveur de PayZen.

    C'est ici que la pub est réellement activée après vérification cryptographique.
    """
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    # Vérifier la signature
    if not verify_signature(request.POST):
        return HttpResponse('Invalid signature', status=400)

    order_id = request.POST.get('vads_order_id', '')
    result   = request.POST.get('vads_result', '')
    status   = request.POST.get('vads_trans_status', '')
    trans_id = request.POST.get('vads_trans_id', '')

    try:
        pub = Publicite.objects.get(payment_ref=order_id)
    except Publicite.DoesNotExist:
        return HttpResponse('Order not found', status=404)

    if result == '00' and status in ('AUTHORISED', 'CAPTURED'):
        # Paiement réussi → activer la pub
        pub.payment_status  = 'paid'
        pub.payment_trans_id = trans_id
        pub.actif           = True
        pub.date_debut      = date.today()
        pub.date_fin        = date.today() + timedelta(weeks=pub.duree_semaines)
        pub.save()
    else:
        # Paiement échoué
        pub.payment_status   = 'failed'
        pub.payment_trans_id = trans_id
        pub.save()

    return HttpResponse('OK', status=200)


@csrf_exempt
def ipn_paiement_rest(request):
    """IPN pour le formulaire embarqué (API REST V4).

    PayZen envoie un POST avec kr-hash et kr-answer.
    """
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    kr_answer = request.POST.get('kr-answer', '')
    kr_hash = request.POST.get('kr-hash', '')

    if not kr_answer or not kr_hash:
        return HttpResponse('Missing kr-answer or kr-hash', status=400)

    # Vérifier la signature
    if not verify_rest_signature(kr_answer, kr_hash):
        logger.warning("IPN REST: invalid signature")
        return HttpResponse('Invalid signature', status=400)

    try:
        answer = json.loads(kr_answer)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    order_id = answer.get('orderDetails', {}).get('orderId', '')
    status = answer.get('orderStatus', '')
    trans_id = answer.get('transactions', [{}])[0].get('uuid', '') if answer.get('transactions') else ''

    try:
        pub = Publicite.objects.get(payment_ref=order_id)
    except Publicite.DoesNotExist:
        return HttpResponse('Order not found', status=404)

    if status == 'PAID':
        pub.payment_status = 'paid'
        pub.payment_trans_id = trans_id
        pub.actif = True
        pub.date_debut = date.today()
        pub.date_fin = date.today() + timedelta(weeks=pub.duree_semaines)
        pub.save()
    elif status in ('UNPAID', 'REFUSED'):
        pub.payment_status = 'failed'
        pub.payment_trans_id = trans_id
        pub.save()

    return HttpResponse('OK', status=200)


@csrf_exempt
def paiement_valide_js(request, pk):
    """Endpoint appelé par le SDK PayZen après paiement (kr-post-url-success).

    Vérifie la signature kr-hash/kr-answer, active la pub,
    puis redirige vers la page de résultat.
    """
    if request.method != 'POST':
        return redirect('deposer_pub')

    kr_answer = request.POST.get('kr-answer', '')
    kr_hash = request.POST.get('kr-hash', '')

    if not kr_answer or not kr_hash:
        messages.error(request, "Données de paiement manquantes.")
        return redirect('deposer_pub')

    if not verify_rest_signature(kr_answer, kr_hash):
        logger.warning("paiement_valide_js: invalid signature for pub %s", pk)
        messages.error(request, "Signature de paiement invalide.")
        return redirect('deposer_pub')

    try:
        answer = json.loads(kr_answer)
    except json.JSONDecodeError:
        messages.error(request, "Données de paiement invalides.")
        return redirect('deposer_pub')

    pub = get_object_or_404(Publicite, pk=pk)

    order_status = answer.get('orderStatus', '')
    trans_id = answer.get('transactions', [{}])[0].get('uuid', '') if answer.get('transactions') else ''

    if order_status == 'PAID' and pub.payment_status == 'pending':
        pub.payment_status = 'paid'
        pub.payment_trans_id = trans_id
        pub.actif = True
        pub.date_debut = date.today()
        pub.date_fin = date.today() + timedelta(weeks=pub.duree_semaines)
        pub.save()

    # Afficher la page de résultat
    success = (pub.payment_status == 'paid')
    return render(request, 'pubs/paiement_resultat.html', {
        'success': success,
        'pub': pub,
    })
