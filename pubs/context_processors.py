from django.core.cache import cache

from .models import Publicite
from ads.models import SOUS_CATEGORIES


def sidebar_pubs(request):
    ctx = cache.get('sidebar_pubs_data')
    if ctx is None:
        # Une seule requete pour toutes les pubs actives
        all_pubs = list(Publicite.objects.filter(actif=True))
        pubs_by_emp = {}
        for pub in all_pubs:
            if pub.emplacement not in pubs_by_emp:
                pubs_by_emp[pub.emplacement] = pub

        ctx = {
            "pub_billboard":     pubs_by_emp.get("billboard"),
            # Sidebar droite
            "pub_sidebar_haut":   pubs_by_emp.get("sidebar_haut"),
            "pub_sidebar_milieu": pubs_by_emp.get("sidebar_milieu"),
            "pub_sidebar_bas":    pubs_by_emp.get("sidebar_bas"),
            # Sidebar gauche
            "pub_sidebar_gauche": pubs_by_emp.get("sidebar_gauche"),
            # Strips accueil
            "pub_strip_accueil_haut":   pubs_by_emp.get("strip_accueil_haut"),
            "pub_strip_accueil_milieu": pubs_by_emp.get("strip_accueil_milieu"),
            "pub_strip_accueil_bas":    pubs_by_emp.get("strip_accueil_bas"),
            "sous_categories": SOUS_CATEGORIES,
        }
        cache.set('sidebar_pubs_data', ctx, 300)

    # unread_count reste hors cache (specifique a chaque utilisateur)
    ctx["unread_count"] = 0
    if request.user.is_authenticated:
        from ads.models import Message
        ctx["unread_count"] = Message.objects.filter(
            to_user=request.user, read=False
        ).count()
    return ctx


def admin_stats(request):
    """Stats injectées dans le dashboard /admin/ uniquement."""
    if not request.path.startswith('/admin/') or not getattr(request.user, 'is_staff', False):
        return {}

    cached = cache.get('admin_stats_data')
    if cached is not None:
        return cached

    try:
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from ads.models import Annonce, Message, Signalement
        from rubriques.models import ArticlePromo, ArticleInfo, ArticleNouveaute
        User = get_user_model()
        sept_jours = timezone.now() - timezone.timedelta(days=7)
        rubriques_attente = (
            ArticlePromo.objects.filter(statut='en_attente').count()
            + ArticleInfo.objects.filter(statut='en_attente').count()
            + ArticleNouveaute.objects.filter(statut='en_attente').count()
        )
        result = {"tbg_stats": {
            "annonces_actives":   Annonce.objects.filter(statut='actif').count(),
            "annonces_moderees":  Annonce.objects.filter(statut='modere').count(),
            "users_total":        User.objects.count(),
            "users_new_7j":       User.objects.filter(date_joined__gte=sept_jours).count(),
            "messages_total":     Message.objects.count(),
            "rubriques_attente":  rubriques_attente,
            "pubs_actives":       Publicite.objects.filter(actif=True).count(),
            "vues_totales":       sum(Annonce.objects.values_list('views', flat=True)),
            "dernières_annonces": Annonce.objects.order_by('-created_at').select_related('user')[:5],
            "signalements":       Signalement.objects.order_by('-created_at').select_related('annonce')[:5],
        }}
        cache.set('admin_stats_data', result, 60)
        return result
    except Exception:
        return {}
