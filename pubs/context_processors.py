from .models import Publicite
from ads.models import SOUS_CATEGORIES


def sidebar_pubs(request):
    ctx = {
        "pub_billboard": Publicite.objects.filter(emplacement="billboard", actif=True).first(),
        "pub_strip_1":   Publicite.objects.filter(emplacement="strip_1",   actif=True).first(),
        "pub_strip_2":   Publicite.objects.filter(emplacement="strip_2",   actif=True).first(),
        "pub_strip_3":   Publicite.objects.filter(emplacement="strip_3",   actif=True).first(),
        "pub_haut":      Publicite.objects.filter(emplacement="haut",      actif=True).first(),
        "pub_milieu":    Publicite.objects.filter(emplacement="milieu",    actif=True).first(),
        "pub_bas":       Publicite.objects.filter(emplacement="bas",       actif=True).first(),
        "sous_categories": SOUS_CATEGORIES,
        "unread_count":    0,
    }
    if request.user.is_authenticated:
        from ads.models import Message
        ctx["unread_count"] = Message.objects.filter(
            to_user=request.user, read=False
        ).count()
    return ctx
