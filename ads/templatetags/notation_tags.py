from django import template
from django.db.models import Avg, Count

register = template.Library()


@register.simple_tag
def vendeur_note(user):
    """
    Retourne un dict avec la note moyenne et le nombre d'avis d'un vendeur.

    Si l'utilisateur n'a pas (encore) de vraies notes via le modele Notation,
    on retombe sur les champs `fake_rating` / `fake_review_count` du modele User
    (utilises uniquement pour l'affichage social — credibiliser le vendeur).

    Usage: {% vendeur_note annonce.user as vn %}
    Puis: {{ vn.moyenne }}, {{ vn.total_avis }}, {{ vn.is_pro }}
    """
    from ads.models import Notation
    stats = Notation.objects.filter(vendeur=user).aggregate(
        moyenne=Avg('note'),
        total_avis=Count('id'),
    )
    moyenne = stats['moyenne']
    total_avis = stats['total_avis'] or 0

    if moyenne is not None:
        r = round(moyenne, 1)
        moyenne = int(r) if r == int(r) else r
    else:
        # Fallback : note d'affichage (fake_rating sur User)
        fake = getattr(user, 'fake_rating', 0) or 0
        if fake and fake > 0:
            moyenne = round(fake, 1)
            total_avis = getattr(user, 'fake_review_count', 0) or 0

    return {
        'moyenne': moyenne,
        'total_avis': total_avis,
        'is_pro': getattr(user, 'role', '') in ('pro', 'admin'),
        'etoiles_pleines': round(moyenne) if moyenne else 0,
    }
