from .models import Publicite
from ads.models import SOUS_CATEGORIES


def sidebar_pubs(request):
    _q = lambda emp: Publicite.objects.filter(emplacement=emp, actif=True).first()
    ctx = {
        "pub_billboard":     _q("billboard"),
        # Sidebar droite
        "pub_sidebar_haut":   _q("sidebar_haut"),
        "pub_sidebar_milieu": _q("sidebar_milieu"),
        "pub_sidebar_bas":    _q("sidebar_bas"),
        # Sidebar gauche
        "pub_sidebar_gauche": _q("sidebar_gauche"),
        # Strips accueil
        "pub_strip_accueil_haut":   _q("strip_accueil_haut"),
        "pub_strip_accueil_milieu": _q("strip_accueil_milieu"),
        "pub_strip_accueil_bas":    _q("strip_accueil_bas"),
        "sous_categories": SOUS_CATEGORIES,
        "unread_count":    0,
    }
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
        return {"tbg_stats": {
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
    except Exception:
        return {}
