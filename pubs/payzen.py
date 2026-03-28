"""
Module utilitaire pour PayZen by OSB.

Supporte deux modes :
 - API Formulaire V2 (redirection) : compute_signature / build_payzen_form
 - API REST V4 (formulaire embarqué) : create_embedded_form_token

Devise : XPF (ISO 4217 n°953, exposant 0 → 1 XPF = 1 unité).
"""
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_key():
    """Retourne la clé active (test ou production) pour l'API Formulaire."""
    if settings.PAYZEN_MODE == 'PRODUCTION':
        return settings.PAYZEN_KEY_PROD
    return settings.PAYZEN_KEY_TEST


def _get_rest_password():
    """Retourne le mot de passe REST API actif."""
    if settings.PAYZEN_MODE == 'PRODUCTION':
        return settings.PAYZEN_REST_API_PASSWORD_PROD
    return settings.PAYZEN_REST_API_PASSWORD_TEST


def _get_public_key():
    """Retourne la clé publique active (pour le SDK JS côté client)."""
    if settings.PAYZEN_MODE == 'PRODUCTION':
        return settings.PAYZEN_PUBLIC_KEY_PROD
    return settings.PAYZEN_PUBLIC_KEY_TEST


def _get_hmac_key():
    """Retourne la clé HMAC active (pour vérifier les retours REST)."""
    if settings.PAYZEN_MODE == 'PRODUCTION':
        return settings.PAYZEN_HMAC_KEY_PROD
    return settings.PAYZEN_HMAC_KEY_TEST


# ═══════════════════════════════════════════════════════════════════════════════
# API Formulaire V2 (redirection — conservé comme fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_signature(form_data, key=None):
    """Calcule la signature HMAC-SHA-256 des champs vads_*.

    1. Trier les champs vads_* par ordre alphabétique
    2. Concaténer leurs valeurs avec '+'
    3. Ajouter la clé après un dernier '+'
    4. HMAC-SHA-256, encoder en base64
    """
    if key is None:
        key = _get_key()
    vads = {k: v for k, v in form_data.items() if k.startswith('vads_')}
    sorted_values = [str(vads[k]) for k in sorted(vads.keys())]
    payload = '+'.join(sorted_values) + '+' + key
    signature = hmac.new(
        key.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')


def build_payzen_form(publicite, request, return_path='/pubs/paiement/retour/', ipn_path='/pubs/paiement/ipn/'):
    """Construit le dict complet des champs pour le formulaire PayZen (redirection).

    Retourne (form_data, payment_url).
    return_path / ipn_path : chemins personnalisables (pour boost, etc.).
    """
    now = datetime.now(timezone.utc)
    trans_id = uuid.uuid4().hex[:6]

    form_data = {
        'vads_site_id':        settings.PAYZEN_SHOP_ID,
        'vads_ctx_mode':       settings.PAYZEN_MODE,
        'vads_trans_date':     now.strftime('%Y%m%d%H%M%S'),
        'vads_trans_id':       trans_id,
        'vads_amount':         str(publicite.prix),
        'vads_currency':       '953',
        'vads_action_mode':    'INTERACTIVE',
        'vads_page_action':    'PAYMENT',
        'vads_payment_config': 'SINGLE',
        'vads_version':        'V2',
        'vads_order_id':       publicite.payment_ref,
        'vads_cust_email':     publicite.client_email,
        'vads_cust_name':      publicite.client_nom,
        'vads_cust_cell_phone': getattr(publicite, 'client_tel', '') or '',
        'vads_order_info':     f"{publicite.get_emplacement_display()} — {publicite.duree_semaines} sem.",
        'vads_return_mode':    'POST',
        'vads_hash_type':      'HMAC_SHA_256',
    }

    base = request.build_absolute_uri('/')[:-1]
    form_data['vads_url_return'] = f"{base}{return_path}"
    form_data['vads_url_check']  = f"{base}{ipn_path}"

    form_data['signature'] = compute_signature(form_data)

    return form_data, settings.PAYZEN_PAYMENT_URL


def verify_signature(post_data):
    """Vérifie la signature d'un retour PayZen (API Formulaire)."""
    received_sig = post_data.get('signature', '')
    if not received_sig:
        return False
    expected_sig = compute_signature(dict(post_data))
    return hmac.compare_digest(received_sig, expected_sig)


# ═══════════════════════════════════════════════════════════════════════════════
# API REST V4 (formulaire embarqué)
# ═══════════════════════════════════════════════════════════════════════════════

REST_API_URL = 'https://secure.osb.pf/api-payment/V4/Charge/CreatePayment'


def create_embedded_form_token(publicite, request, ipn_path='/pubs/paiement/ipn/rest/'):
    """Appelle l'API REST PayZen pour créer un formToken (formulaire embarqué).

    Retourne (form_token, public_key) ou lève une exception en cas d'erreur.
    ipn_path : chemin IPN (défaut pubs, peut être changé pour boost).
    """
    password = _get_rest_password()
    shop_id = settings.PAYZEN_SHOP_ID

    # Auth HTTP Basic : shop_id:password
    credentials = base64.b64encode(f"{shop_id}:{password}".encode()).decode()

    base_url = request.build_absolute_uri('/')[:-1]

    billing = {'firstName': publicite.client_nom}
    if getattr(publicite, 'client_tel', ''):
        billing['cellPhoneNumber'] = publicite.client_tel

    payload = {
        'amount': publicite.prix,
        'currency': 'XPF',
        'orderId': publicite.payment_ref,
        'customer': {
            'email': publicite.client_email,
            'billingDetails': billing,
        },
        'ipnTargetUrl': f"{base_url}{ipn_path}",
    }

    body = json.dumps(payload).encode('utf-8')

    req = Request(REST_API_URL, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Basic {credentials}')

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except URLError as e:
        logger.error("PayZen REST API error: %s", e)
        raise RuntimeError(f"Erreur de connexion PayZen : {e}")

    if data.get('status') != 'SUCCESS':
        error_msg = data.get('answer', {}).get('errorMessage', str(data))
        logger.error("PayZen CreatePayment failed: %s", error_msg)
        raise RuntimeError(f"Erreur PayZen : {error_msg}")

    form_token = data['answer']['formToken']
    public_key = _get_public_key()

    return form_token, public_key


def verify_rest_signature(kr_answer, kr_hash):
    """Vérifie la signature d'un retour du formulaire embarqué (IPN REST ou JS callback).

    kr_answer : la réponse JSON brute (string)
    kr_hash   : le hash reçu (kr-hash header ou champ POST)
    """
    hmac_key = _get_hmac_key()
    expected = hmac.new(
        hmac_key.encode('utf-8'),
        kr_answer.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, kr_hash)
