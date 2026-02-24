"""
Management command : python manage.py seed_rubriques
Cree des articles Promo, Info et Nouveaute factices pour tester le rendu.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rubriques.models import ArticlePromo, ArticleInfo, ArticleNouveaute

User = get_user_model()
SEED_TAG = '[SEED]'

PROMOS = [
    {
        'titre': '-25% sur l\'electromenager — Carrefour Papeete',
        'contenu': (
            'Jusqu\'au 31 mars, profitez de -25% sur toute la gamme electromenager : '
            'refrigerateurs, lave-linges, cuisinieres, micro-ondes... Offre valable en magasin '
            'et sur carrefour.pf. Non cumulable avec d\'autres promotions en cours. '
            'Stocks limites, dans la limite des stocks disponibles.'
        ),
        'lien': 'https://www.carrefour.pf',
    },
    {
        'titre': 'Hi-Fi Store : iPhones reconditionnés Grade A a partir de 45 000 XPF',
        'contenu': (
            'Retrouvez chez Hi-Fi Store Punaauia une large selection d\'iPhones et Samsung '
            'reconditionnés Grade A et B certifies. Garantie 6 mois incluse. '
            'Possibilite de reprise de votre ancien appareil avec estimation sur place. '
            'Ouvert du lundi au samedi de 8h a 18h. Contactez-nous au 89 XX XX XX.'
        ),
        'lien': '',
    },
    {
        'titre': 'Shell Tahiti : 1 plein = 1 lavage auto gratuit',
        'contenu': (
            'Pour tout plein d\'au moins 5 000 XPF realise dans les stations Shell de Papeete, '
            'Punaauia ou Faa\'a, beneficiez d\'un bon de lavage auto gratuit valeur 1 500 XPF. '
            'Offre valable du 1er au 30 mars 2025. Un bon par vehicule et par passage. '
            'Non valable avec les cartes professionnelles Fleet.'
        ),
        'lien': '',
    },
    {
        'titre': 'Bricorama Pirae : -30% peinture Dulux Valentine & Tollens',
        'contenu': (
            'Grande promo peinture chez Bricorama Pirae. Toute la gamme Dulux Valentine et Tollens '
            'a -30% : peintures interieures, exterieures, sous-couches, vernis et lasures. '
            'Disponible en magasin uniquement. Des conseillers sont disponibles pour vous aider '
            'a choisir couleurs et finitions. Valable jusqu\'au stock epuise.'
        ),
        'lien': '',
    },
    {
        'titre': 'Pacific Automobile : financement 0% sur 24 mois — Toyota & Mitsubishi',
        'contenu': (
            'Pacific Automobile vous offre un financement a 0% d\'interets sur 24 mois pour '
            'tout achat d\'un vehicule neuf Toyota ou Mitsubishi neuf. Offre reservee aux '
            'dossiers acceptes, sous reserve de l\'accord du partenaire bancaire Ofina. '
            'Valable jusqu\'au 15 avril 2025. Renseignez-vous en concession a Faa\'a.'
        ),
        'lien': '',
    },
    {
        'titre': 'Fenua Sport : chaussures running Nike & Asics a -20%',
        'contenu': (
            'Pour les passionnes de course a pied : chaussures Nike Air Zoom, Asics Gel-Nimbus '
            'et Brooks Ghost a -20% tout le mois de mars. Aussi en promo : tenues de sport, '
            'montres GPS Garmin Forerunner et accessoires fitness. '
            'Profitez-en pour preparer le Tahiti Nui Trail en mai !'
        ),
        'lien': '',
    },
    {
        'titre': 'Air Tahiti Nui : vols PPT-LAX des 89 000 XPF TTC',
        'contenu': (
            'Vols Papeete vers Los Angeles des 89 000 XPF TTC et vers Paris des 129 000 XPF TTC. '
            'Reservation avant le 31 mars 2025, voyage jusqu\'au 30 juin 2025. '
            'Tarifs incluant les bagages en soute (1 x 23 kg), taxes et surcharges. '
            'Modification possible avec frais. Connectez-vous sur airtahitinui.com.'
        ),
        'lien': 'https://www.airtahitinui.com',
    },
    {
        'titre': 'MANA Fibre : 50% offerts le premier mois — code MANATBG',
        'contenu': (
            'Passez a la fibre MANA et beneficiez de 50% de reduction sur votre premiere '
            'mensualite. Offre valable pour tout nouveau client fibre, sur presentation du '
            'code promo MANATBG2025 au moment de la souscription. '
            'Installation gratuite si souscription avant le 30 avril 2025. '
            'Debit garanti jusqu\'a 100 Mb/s en download.'
        ),
        'lien': 'https://www.mana.pf',
    },
    {
        'titre': 'Tama\'a Maitai : menu dejeuner complet a 1 500 XPF',
        'contenu': (
            'Tous les midis en semaine, le restaurant Tama\'a Maitai a Papeete vous propose '
            'un menu dejeuner complet a 1 500 XPF : entree + plat du jour tahitien (poisson '
            'cru, maa tinito, chow mein...) + dessert maison + jus de fruit frais. '
            'Sur reservation au 87 XX XX XX ou en walk-in selon disponibilites. '
            'Parking gratuit pour les clients.'
        ),
        'lien': '',
    },
    {
        'titre': 'Avis Polynesia : -15% location voitures Moorea avec MOOREAAVIS15',
        'contenu': (
            'Visitez Moorea en toute liberte avec AVIS Polynesie. Profitez de -15% sur toutes '
            'les locations de vehicules a Moorea en reservant en ligne avec le code MOOREAAVIS15. '
            'Valable pour tout sejour du 15 mars au 30 juin 2025. '
            'Kilometrage illimite inclus, assurance CDW disponible en supplement. '
            'Retrait et restitution a la gare maritime de Vaiare.'
        ),
        'lien': '',
    },
]


class Command(BaseCommand):
    help = 'Cree des articles Promo/Info/Nouveaute factices pour le rendu du site'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Supprime les articles [SEED] existants avant recreation')

    def handle(self, *args, **options):
        if options['reset']:
            dp, _ = ArticlePromo.objects.filter(titre__startswith=SEED_TAG).delete()
            self.stdout.write(self.style.WARNING(f'  {dp} promos [SEED] supprimees.'))

        seed_email = 'seed@tbg.pf'
        user, created = User.objects.get_or_create(
            email=seed_email,
            defaults={'nom': 'Vendeur TBG', 'role': 'pro', 'is_active': True},
        )
        if created:
            user.set_password('seed_password_tbg_2025')
            user.save()

        total = 0
        for p in PROMOS:
            titre_seed = f"{SEED_TAG} {p['titre']}"
            if ArticlePromo.objects.filter(titre=titre_seed).exists():
                continue
            ArticlePromo.objects.create(
                pro_user=user,
                titre=titre_seed,
                contenu=p['contenu'],
                lien_promo=p['lien'],
                statut='valide',
            )
            total += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] {total} promos factices creees.'
        ))
        self.stdout.write(
            '   Pour les supprimer : python manage.py seed_rubriques --reset\n'
        )
