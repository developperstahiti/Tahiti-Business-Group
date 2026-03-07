"""
Management command : python manage.py seed_rubriques
Supprime toutes les rubriques existantes et cree 9 vrais articles avec photos.
"""
import io
import ssl
import urllib.request

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from rubriques.models import ArticlePromo, ArticleInfo, ArticleNouveaute
from ads.image_utils import save_webp

User = get_user_model()


def _download(url):
    """Telecharge une image et retourne les bytes, ou None si echec."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return urllib.request.urlopen(req, context=ctx, timeout=15).read()
    except Exception:
        return None


def _attach(article, img_url, prefix):
    """Telecharge img_url, convertit en WebP, et attache a l'article."""
    data = _download(img_url)
    if not data:
        return
    fobj = InMemoryUploadedFile(
        io.BytesIO(data), 'photo', 'img.jpg', 'image/jpeg', len(data), None
    )
    url = save_webp(fobj, 'rubriques', f'{prefix}_{article.pk}')
    article.photo = url
    article.save()
    return url


# ── Donnees ──────────────────────────────────────────────────────────

INFOS = [
    {
        'titre': "Le tourisme en Polynesie depasse les 300 000 visiteurs en 2025",
        'contenu': (
            "La Polynesie francaise a accueilli plus de 300 000 touristes en 2025, "
            "un record historique pour le territoire. Selon les chiffres du Service du tourisme, "
            "cette hausse de 12% par rapport a 2024 s'explique par le renforcement des liaisons "
            "aeriennes et la visibilite accrue de la destination apres les Jeux Olympiques de "
            "Paris 2024, dont les epreuves de surf se sont tenues a Teahupo'o.\n\n"
            "Les iles Sous-le-Vent (Bora Bora, Raiatea, Huahine) restent les plus visitees, "
            "suivies de Tahiti et Moorea. Le secteur represente desormais pres de 15% du PIB "
            "du territoire. Les autorites souhaitent developper un tourisme durable et mieux "
            "repartir les flux sur l'ensemble des archipels."
        ),
        'img': 'https://images.unsplash.com/photo-1589197331516-4d84b72ebde3?w=800&q=80',
    },
    {
        'titre': "Air Tahiti Nui renforce ses liaisons vers le Japon et la Nouvelle-Zelande",
        'contenu': (
            "La compagnie aerienne Air Tahiti Nui a annonce l'ouverture de deux nouvelles "
            "frequences hebdomadaires vers Tokyo-Narita et Auckland a compter de juin 2026. "
            "Cette decision repond a une demande croissante des voyageurs asiatiques et "
            "oceaniens pour la destination polynesienne.\n\n"
            "Avec sa flotte de Boeing 787-9 Dreamliner, la compagnie dessert deja Paris, "
            "Los Angeles, Seattle et Auckland. Ces nouvelles liaisons permettront de diversifier "
            "la clientele touristique et de renforcer les echanges commerciaux avec la zone "
            "Asie-Pacifique. Des tarifs promotionnels seront proposes pour les premiers vols."
        ),
        'img': 'https://images.unsplash.com/photo-1569154941061-e231b4725ef1?w=800&q=80',
    },
    {
        'titre': "Papeete : le marche municipal fait peau neuve apres 18 mois de travaux",
        'contenu': (
            "Le celebre Marche de Papeete a rouvert ses portes apres un chantier de renovation "
            "de 18 mois. Les travaux, finances par le Pays et la commune pour un montant de "
            "1,2 milliard de francs CFP, ont permis de moderniser les installations tout en "
            "preservant le caractere authentique du lieu.\n\n"
            "Les 200 commercants retrouvent des etals renoves, une meilleure ventilation "
            "naturelle, et un espace restauration agrandi au premier etage. Le marche, qui "
            "existe depuis 1847, reste un incontournable pour les locaux comme pour les "
            "touristes, avec ses fleurs de tiare, son poisson cru et son artisanat local."
        ),
        'img': 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80',
    },
]

NOUVEAUTES = [
    {
        'titre': "Ouverture de Mana Hub, premier espace de coworking premium a Papeete",
        'contenu': (
            "Mana Hub ouvre ses portes au coeur de Papeete, dans le quartier du front de mer. "
            "Cet espace de coworking de 400 m2 propose des bureaux partages, des salles de "
            "reunion equipees, et un espace detente avec vue sur le port.\n\n"
            "Concu pour les freelances, startups et tele-travailleurs, Mana Hub offre une "
            "connexion fibre optique haut debit, un service d'impression 3D, et un programme "
            "de networking mensuel. Les tarifs demarrent a 15 000 XPF/mois pour un poste fixe. "
            "L'espace accueille deja une vingtaine de professionnels du numerique, du design "
            "et du conseil."
        ),
        'img': 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80',
    },
    {
        'titre': "Hina Brewing Co. : la premiere brasserie artisanale 100% polynesienne",
        'contenu': (
            "Hina Brewing Co. lance sa gamme de bieres artisanales brassees a Tahiti avec des "
            "ingredients locaux. La jeune brasserie, fondee par deux entrepreneurs de Punaauia, "
            "propose trois references : une blonde legere au fruit de la passion, une IPA aux "
            "agrumes de Moorea, et une stout au cacao de Raiatea.\n\n"
            "Disponibles dans une trentaine de restaurants et magasins de Tahiti, ces bieres "
            "se demarquent par leur identite polynesienne affirmee. La brasserie prevoit "
            "d'ouvrir un taproom avec terrasse d'ici fin 2026. Une demarche eco-responsable "
            "est au coeur du projet : bouteilles consignees, draches donnees aux eleveurs locaux."
        ),
        'img': 'https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=800&q=80',
    },
    {
        'titre': "FenUA Express : nouveau service de livraison a domicile sur Tahiti",
        'contenu': (
            "FenUA Express lance son service de livraison a domicile couvrant toute l'ile de "
            "Tahiti. Commandez en ligne et recevez vos courses, repas ou colis en moins de "
            "2 heures. Le service fonctionne 7 jours sur 7, de 8h a 21h.\n\n"
            "L'application mobile (iOS et Android) permet de suivre sa livraison en temps reel. "
            "Les commercants locaux peuvent s'inscrire comme partenaires pour proposer leurs "
            "produits sur la plateforme. FenUA Express emploie deja 25 livreurs en scooter "
            "electrique et prevoit de s'etendre a Moorea debut 2027."
        ),
        'img': 'https://images.unsplash.com/photo-1526367790999-0150786686a2?w=800&q=80',
    },
]

PROMOS = [
    {
        'titre': "-30% sur les bungalows sur pilotis a Moorea jusqu'au 30 juin",
        'contenu': (
            "La Pension Teavaro de Moorea propose une offre exceptionnelle : -30% sur ses "
            "bungalows sur pilotis pour tout sejour de 3 nuits minimum reserve avant le "
            "30 juin 2026. Petit-dejeuner polynesien inclus.\n\n"
            "Situee sur la baie de Cook avec vue directe sur le mont Rotui, la pension offre "
            "un cadre idyllique avec acces direct au lagon. Activites incluses : kayak, "
            "palmes-masque-tuba, et excursion dauphins. Tarif a partir de 18 000 XPF/nuit "
            "au lieu de 26 000 XPF. Reservation par telephone au 87 56 78 90 ou par email."
        ),
        'img': 'https://images.unsplash.com/photo-1544550581-5f7ceaf7f992?w=800&q=80',
    },
    {
        'titre': "Cours de surf a Teahupo'o : pack decouverte a 5 000 XPF",
        'contenu': (
            "Teahupo'o Surf School propose un pack decouverte exceptionnel : 2 heures de "
            "cours collectif + location de planche pour seulement 5 000 XPF (au lieu de "
            "8 500 XPF). Offre valable tous les samedis matins jusqu'en septembre 2026.\n\n"
            "Les cours sont encadres par des moniteurs diplomes et adaptes a tous les niveaux, "
            "du debutant complet au surfeur intermediaire. Le spot choisi offre des conditions "
            "ideales pour l'apprentissage : vagues regulieres et fond sableux. Combinaison "
            "et lycra fournis. Inscriptions sur place ou au 87 12 34 56."
        ),
        'img': 'https://images.unsplash.com/photo-1455729552865-3658a5d39692?w=800&q=80',
    },
    {
        'titre': "Plongee a Rangiroa : bapteme offert pour tout sejour de 5 jours",
        'contenu': (
            "Le centre de plongee Blue Lagoon Diving de Rangiroa offre un bapteme de plongee "
            "gratuit pour toute reservation d'un sejour plongee de 5 jours ou plus. Explorez "
            "la passe de Tiputa, celebre pour ses requins, dauphins et raies manta.\n\n"
            "Le centre, certifie PADI 5 etoiles, propose des sorties quotidiennes encadrees "
            "par des moniteurs francophones et anglophones. Materiel recent Aqualung inclus. "
            "L'offre est valable jusqu'au 31 decembre 2026 et cumulable avec les tarifs groupe "
            "(a partir de 4 plongeurs). Renseignements : contact@bluelagoondiving.pf"
        ),
        'img': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&q=80',
    },
]


class Command(BaseCommand):
    help = 'Supprime toutes les rubriques et cree 9 vrais articles avec photos'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='(legacy) Meme effet que sans flag : reset complet')

    def handle(self, *args, **options):
        # Supprimer toutes les rubriques
        d1 = ArticleInfo.objects.all().delete()
        d2 = ArticleNouveaute.objects.all().delete()
        d3 = ArticlePromo.objects.all().delete()
        self.stdout.write(self.style.WARNING(
            f"Supprime: {d1[0]} infos, {d2[0]} nouveautes, {d3[0]} promos"
        ))

        # Trouver un admin ou pro user
        user = (
            User.objects.filter(role='admin').first()
            or User.objects.filter(role='pro').first()
        )
        if not user:
            user, _ = User.objects.get_or_create(
                email='seed@tbg.pf',
                defaults={'nom': 'TBG Admin', 'role': 'pro', 'is_active': True},
            )
            if _:
                user.set_password('seed_tbg_2026')
                user.save()

        # Creer les infos
        for data in INFOS:
            article = ArticleInfo.objects.create(
                auteur=user,
                titre=data['titre'],
                contenu=data['contenu'],
                statut='valide',
            )
            url = _attach(article, data['img'], 'info')
            self.stdout.write(f"  Info: {article.titre[:50]}... photo={'OK' if url else 'FAIL'}")

        # Creer les nouveautes
        for data in NOUVEAUTES:
            article = ArticleNouveaute.objects.create(
                pro_user=user,
                titre=data['titre'],
                contenu=data['contenu'],
                statut='valide',
            )
            url = _attach(article, data['img'], 'nouv')
            self.stdout.write(f"  Nouv: {article.titre[:50]}... photo={'OK' if url else 'FAIL'}")

        # Creer les promos
        for data in PROMOS:
            article = ArticlePromo.objects.create(
                pro_user=user,
                titre=data['titre'],
                contenu=data['contenu'],
                statut='valide',
            )
            url = _attach(article, data['img'], 'promo')
            self.stdout.write(f"  Promo: {article.titre[:50]}... photo={'OK' if url else 'FAIL'}")

        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] {ArticleInfo.objects.count()} infos, "
            f"{ArticleNouveaute.objects.count()} nouveautes, "
            f"{ArticlePromo.objects.count()} promos creees avec photos."
        ))
