from django import template
from django.db.models import Avg, Count

register = template.Library()


@register.simple_tag
def vendeur_note(user):
    """
    Retourne un dict avec la note moyenne et le nombre d'avis d'un vendeur.
    Usage: {% vendeur_note annonce.user as vn %}
    Puis: {{ vn.moyenne }}, {{ vn.total_avis }}, {{ vn.is_pro }}
    """
    from ads.models import Notation
    stats = Notation.objects.filter(vendeur=user).aggregate(
        moyenne=Avg('note'),
        total_avis=Count('id'),
    )
    moyenne = stats['moyenne']
    if moyenne is not None:
        moyenne = round(moyenne, 1)
    return {
        'moyenne': moyenne,
        'total_avis': stats['total_avis'],
        'is_pro': getattr(user, 'role', '') in ('pro', 'admin'),
        'etoiles_pleines': round(moyenne) if moyenne else 0,
    }
