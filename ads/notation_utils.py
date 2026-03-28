from django.db.models import Avg, Count, Q, Value, IntegerField

from ads.models import Annonce, Message, Notation  # noqa: F401 (Message used by taux_reponse)

MOIS_FR = {
    1: 'janvier',
    2: 'février',
    3: 'mars',
    4: 'avril',
    5: 'mai',
    6: 'juin',
    7: 'juillet',
    8: 'août',
    9: 'septembre',
    10: 'octobre',
    11: 'novembre',
    12: 'décembre',
}


def peut_noter(acheteur, vendeur):
    """
    Retourne True si l'acheteur peut noter le vendeur.

    Conditions :
    - acheteur != vendeur
    - aucune notation n'existe déjà pour ce couple (acheteur, vendeur)
    """
    if acheteur == vendeur:
        return False

    deja_note = Notation.objects.filter(
        acheteur=acheteur,
        vendeur=vendeur,
    ).exists()

    return not deja_note


def note_moyenne(vendeur):
    """
    Retourne la moyenne des notes et le nombre total d'avis pour un vendeur.

    Retour : {'moyenne': float arrondi 1 décimale ou None, 'total_avis': int}
    """
    stats = Notation.objects.filter(vendeur=vendeur).aggregate(
        moyenne=Avg('note'),
        total_avis=Count('id'),
    )

    moyenne = stats['moyenne']
    if moyenne is not None:
        moyenne = round(moyenne, 1)

    return {
        'moyenne': moyenne,
        'total_avis': stats['total_avis'],
    }


def taux_reponse(vendeur):
    """
    Calcule le pourcentage de conversations où le vendeur a répondu au moins une fois.

    Une "conversation" = ensemble de messages reçus par le vendeur, groupés par
    (from_user, annonce). Le vendeur a "répondu" s'il existe au moins un Message
    avec from_user=vendeur, to_user=acheteur, annonce=même annonce.

    Retourne un int (pourcentage arrondi). Si aucune conversation, retourne 100.
    """
    # Toutes les conversations distinctes reçues par le vendeur
    conversations = (
        Message.objects
        .filter(to_user=vendeur)
        .values('from_user', 'annonce')
        .distinct()
    )

    total = conversations.count()
    if total == 0:
        return 100

    repondues = 0
    for conv in conversations:
        a_repondu = Message.objects.filter(
            from_user=vendeur,
            to_user=conv['from_user'],
            annonce=conv['annonce'],
        ).exists()
        if a_repondu:
            repondues += 1

    return round(repondues * 100 / total)


def distribution_notes(vendeur):
    """
    Retourne la distribution des notes pour un vendeur.
    Retour : {5: count, 4: count, 3: count, 2: count, 1: count}
    """
    counts = (
        Notation.objects.filter(vendeur=vendeur)
        .values('note')
        .annotate(count=Count('id'))
    )
    dist = {i: 0 for i in range(1, 6)}
    for entry in counts:
        dist[entry['note']] = entry['count']
    return dist


def stats_vendeur(vendeur):
    """
    Retourne un dictionnaire complet de statistiques pour un vendeur.
    """
    notes = note_moyenne(vendeur)

    date = vendeur.date_joined
    membre_depuis = f"{MOIS_FR[date.month]} {date.year}"

    nb_annonces = Annonce.objects.filter(user=vendeur, statut='actif').count()

    is_pro = vendeur.role in ('pro', 'admin')

    return {
        'note_moyenne': notes['moyenne'],
        'total_avis': notes['total_avis'],
        'taux_reponse': taux_reponse(vendeur),
        'membre_depuis': membre_depuis,
        'nb_annonces': nb_annonces,
        'badge': 'Professionnel' if is_pro else 'Particulier',
        'is_pro': is_pro,
    }
