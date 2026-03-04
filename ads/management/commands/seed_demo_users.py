"""
python manage.py seed_demo_users          → crée 10 utilisateurs + 20 annonces avec photos
python manage.py seed_demo_users --reset  → supprime et recrée tout
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from ads.models import Annonce

User = get_user_model()

# ── Photos Picsum stables (seed = toujours la même image) ─────────────────────
# Format : https://picsum.photos/seed/{mot}/900/600
def _photo(seed):
    return f"https://picsum.photos/seed/{seed}/900/600"

# ── 10 utilisateurs polynésiens ───────────────────────────────────────────────
DEMO_USERS = [
    {'email': 'mahana.teriitua@demo.pf',    'nom': 'Mahana Teriitua',     'tel': '87 23 45 67', 'role': 'personnel'},
    {'email': 'heiarii.tamatoa@demo.pf',    'nom': 'Heiarii Tamatoa',     'tel': '87 54 12 89', 'role': 'pro',       'entreprise': 'Tamatoa Auto'},
    {'email': 'maeva.temarii@demo.pf',      'nom': 'Maeva Temarii',       'tel': '89 11 22 33', 'role': 'personnel'},
    {'email': 'raitea.hauata@demo.pf',      'nom': 'Raitea Hauata',       'tel': '87 66 77 88', 'role': 'personnel'},
    {'email': 'tetuanui.maraeura@demo.pf',  'nom': 'Tetuanui Maraeura',   'tel': '89 44 55 66', 'role': 'pro',       'entreprise': 'Hotel Maraeura'},
    {'email': 'vaite.teihotaata@demo.pf',   'nom': 'Vaite Teihotaata',    'tel': '87 33 21 09', 'role': 'personnel'},
    {'email': 'hinanui.teariki@demo.pf',    'nom': 'Hinanui Teariki',     'tel': '87 88 99 00', 'role': 'personnel'},
    {'email': 'teva.paruru@demo.pf',        'nom': 'Teva Paruru',         'tel': '89 77 66 55', 'role': 'pro',       'entreprise': 'Paruru Transport'},
    {'email': 'anani.tupaia@demo.pf',       'nom': 'Anani Tupaia',        'tel': '87 12 34 56', 'role': 'personnel'},
    {'email': 'moana.tetuanui@demo.pf',     'nom': 'Moana Tetuanui',      'tel': '89 55 44 33', 'role': 'personnel'},
]

# ── 20 annonces (2 par utilisateur, index 0-1 = user 0, 2-3 = user 1 …) ────
DEMO_ANNONCES = [
    # ── Māhana Teriitua ───────────────────────────────────────────────────────
    {
        'titre': 'Toyota Prado 2019 — 4x4 diesel, full options',
        'description': (
            'Prado TXL 2019, 78 000 km, boîte automatique 6 rapports, moteur 3.0L diesel. '
            'Équipé : cuir beige, toit ouvrant panoramique, caméra 360°, Apple CarPlay, '
            'jantes 18" alloy. Carnet d\'entretien complet, révisé en janvier 2025. '
            'Première main, non accidenté. Disponible immédiatement à Papeete.'
        ),
        'prix': 3500000, 'categorie': 'vehicules', 'sous_categorie': 'vehicules-4x4',
        'localisation': 'Papeete',
        'photos': [_photo('suv-offroad'), _photo('car-interior')],
    },
    {
        'titre': 'Villa T3 vue lagon — Punaauia, piscine, terrain 600m²',
        'description': (
            'Magnifique villa de 110m² sur terrain 600m², vue imprenable sur le lagon de '
            'Punaauia et Moorea. 3 chambres dont une suite parentale avec dressing, '
            '2 salles de bain, cuisine ouverte équipée, salon cathédrale. Piscine 8×4m, '
            'carport 2 voitures, jardin paysager tropical. Secteur résidentiel calme, '
            'à 10 min du centre de Papeete. Aucun travaux à prévoir.'
        ),
        'prix': 45000000, 'categorie': 'immobilier', 'sous_categorie': 'immo-maisons',
        'localisation': 'Punaauia',
        'photos': [_photo('villa-pool'), _photo('tropical-garden')],
    },

    # ── Heiarii Tamatoa ───────────────────────────────────────────────────────
    {
        'titre': 'iPhone 15 Pro 256 Go — titane naturel, parfait état',
        'description': (
            'iPhone 15 Pro 256 Go en titane naturel, acheté en novembre 2024 chez Apple '
            'Store Sydney. Encore sous garantie Apple jusqu\'en novembre 2025. '
            'Toujours utilisé avec coque MagSafe Nomad et protection d\'écran en verre '
            'trempé. Autonomie excellente (batterie à 98%). Boîte d\'origine, câble USB-C '
            'et adaptateur inclus. Débloqué tous opérateurs.'
        ),
        'prix': 120000, 'categorie': 'electronique', 'sous_categorie': 'elec-telephones',
        'localisation': "Faa'a",
        'photos': [_photo('iphone-titanium'), _photo('smartphone-desk')],
    },
    {
        'titre': 'Scooter Yamaha NMAX 155 — 2022, 11 000 km, bleu',
        'description': (
            'Yamaha NMAX 155 ABS 2022, 11 000 km, couleur bleu nuit. Freins ABS avant/arrière, '
            'démarrage sans clé (keyless), topcase SHAD 35L inclus, rétroviseurs carbone. '
            'Vidange faite à 10 000 km, pneus à 70%. Contrôle technique valide juin 2026. '
            'Parfait pour circuler à Papeete. Carte grise Polynésie. Prix ferme.'
        ),
        'prix': 290000, 'categorie': 'vehicules', 'sous_categorie': 'vehicules-2roues',
        'localisation': "Faa'a",
        'photos': [_photo('scooter-blue'), _photo('scooter-parking')],
    },

    # ── Maeva Temarii ─────────────────────────────────────────────────────────
    {
        'titre': 'Cours de Pilates — Papeete, tous niveaux',
        'description': (
            'Formatrice certifiée Pilates méthode STOTT, 7 ans d\'expérience. Cours '
            'individuels ou en duo, à votre domicile ou en studio à Papeete (Quartier du '
            'Commerce). Programme adapté : débutant, grossesse, post-partum, douleurs dorsales. '
            'Matériel fourni. Première séance d\'évaluation gratuite. '
            'Disponible lundi au samedi, 7h–19h. Réservation WhatsApp uniquement.'
        ),
        'prix': 3500, 'prix_label': '3 500 XPF / séance',
        'categorie': 'services', 'sous_categorie': 'services-cours',
        'localisation': 'Papeete',
        'photos': [_photo('pilates-class'), _photo('yoga-mat')],
    },
    {
        'titre': 'Canapé d\'angle cuir noir 5 places — convertible',
        'description': (
            'Canapé d\'angle convertible 5 places en cuir noir, méridienne côté gauche avec '
            'coffre de rangement intégré. Dimensions : 290×160cm. 2 ans et demi d\'utilisation '
            'dans appartement non-fumeur, sans animaux. Coussins inclus. Aucune déchirure ni '
            'tâche. Vendu car déménagement. À enlever à Pirae — camion de déménagement '
            'possible à prix coûtant.'
        ),
        'prix': 45000, 'categorie': 'autres', 'sous_categorie': 'autres-meubles',
        'localisation': 'Pirae',
        'photos': [_photo('black-sofa'), _photo('living-room')],
    },

    # ── Raitea Hauata ─────────────────────────────────────────────────────────
    {
        'titre': 'Location saisonnière Moorea — bungalow lagon, 4 pers',
        'description': (
            'Bungalow sur pilotis, accès direct au lagon de Moorea, vue sur Tahiti. '
            'Capacité 4 personnes : chambre avec lit king + convertible salon. Cuisine '
            'équipée, terrasse avec hamac et table, kayaks et palmes fournis. Wifi haut '
            'débit. À 5 min en pirogue du motu. Disponible toute l\'année. '
            'Minimum 2 nuits. Ménage inclus. Caution 20 000 XPF.'
        ),
        'prix': 18000, 'prix_label': '18 000 XPF / nuit',
        'categorie': 'immobilier', 'sous_categorie': 'immo-saisonnieres',
        'localisation': 'Moorea',
        'photos': [_photo('overwater-bungalow'), _photo('lagoon-tropical')],
    },
    {
        'titre': 'Jet-ski Sea-Doo Spark Trixx 90CV — 2021, orange',
        'description': (
            'Sea-Doo Spark Trixx 90CV 2021, couleur orange et blanc. 52 heures moteur '
            'seulement. Rangé sous abri depuis achat. Gilets de sauvetage homologués '
            '(x2) inclus, housse de protection, remorque monoaxe. '
            'Révisé en octobre 2024. Parfait pour famille ou débutant. '
            'Vendu car achat d\'un bateau. Prix à débattre légèrement.'
        ),
        'prix': 1100000, 'categorie': 'vehicules', 'sous_categorie': 'vehicules-bateaux',
        'localisation': 'Moorea',
        'photos': [_photo('jetski-orange'), _photo('sea-water-sport')],
    },

    # ── Tetuanui Maraeura ─────────────────────────────────────────────────────
    {
        'titre': 'Chef de rang — restaurant gastronomique Papeete',
        'description': (
            'Hôtel Maraeura Papeete recrute un(e) chef de rang expérimenté(e) pour son '
            'restaurant gastronomique (90 couverts, carte fusion franco-polynésienne). '
            'Service soir uniquement 18h–23h, 5 jours sur 7. Exigences : expérience fine '
            'dining minimum 2 ans, présentation irréprochable, maîtrise service en salle '
            'et conseil vins. Salaire attractif + pourboires + mutuelle. CDI après essai 1 mois.'
        ),
        'prix': 0, 'prix_label': '190 000 XPF/mois + pourboires',
        'categorie': 'emploi', 'sous_categorie': 'emploi-hotellerie',
        'localisation': 'Papeete',
        'photos': [_photo('restaurant-fine-dining'), _photo('gastronomie-table')],
    },
    {
        'titre': 'MacBook Pro M3 14" — 16Go/512Go, 3 mois, parfait état',
        'description': (
            'MacBook Pro 14 pouces, puce Apple M3, 16 Go RAM, SSD 512 Go. Acheté en '
            'décembre 2024, encore sous garantie Apple. Autonomie 18 heures. Écran '
            'Liquid Retina XDR 3024×1964 pixels. Couleur noir sidéral. '
            'Utilisé uniquement en bureautique, aucune rayure. Chargeur MagSafe 96W, '
            'câble USB-C, boîte d\'origine. Vendu car changement de poste (fourni par employeur).'
        ),
        'prix': 290000, 'categorie': 'electronique', 'sous_categorie': 'elec-ordinateurs',
        'localisation': 'Punaauia',
        'photos': [_photo('macbook-pro-desk'), _photo('laptop-minimal')],
    },

    # ── Vaite Teihotaata ──────────────────────────────────────────────────────
    {
        'titre': 'Terrain 800m² viabilisé — Mahina, bord de route',
        'description': (
            'Beau terrain plat de 800m² entièrement viabilisé à Mahina, en bord de route '
            'secondaire. Eau CDE en limite de propriété, électricité EDT à 5m, tout à '
            'l\'égout. Plan cadastral disponible. Certificat d\'urbanisme obtenu, '
            'constructibilité confirmée. Idéal construction villa ou duplex. '
            'Voisinage calme, à 15 min de Papeete. Propriétaire direct, pas d\'agence.'
        ),
        'prix': 9500000, 'categorie': 'immobilier', 'sous_categorie': 'immo-terrains',
        'localisation': 'Mahina',
        'photos': [_photo('tropical-land'), _photo('green-field-tahiti')],
    },
    {
        'titre': 'Longboard surf 9\'2 Noosa — + leash + housse',
        'description': (
            'Longboard Noosa Surfboards 9\'2", shape single fin classique, volume 72L. '
            'Idéal pour vagues molles de Polynésie (Papara, Taapuna). '
            'Acheté neuf il y a 2 ans, utilisé une trentaine de fois. '
            'Quelques petites égratignures de wax sur le deck, rien de structurel. '
            'Livré avec leash 9\' et housse de transport. Vendeur passionné, '
            'renseignements par WhatsApp uniquement.'
        ),
        'prix': 55000, 'categorie': 'autres', 'sous_categorie': 'autres-sport',
        'localisation': 'Mahina',
        'photos': [_photo('longboard-surf'), _photo('surfboard-ocean')],
    },

    # ── Hinanui Teariki ───────────────────────────────────────────────────────
    {
        'titre': 'Studio meublé Bora Bora — vue montagne, tout inclus',
        'description': (
            'Studio de 32m² entièrement meublé et équipé, situé à Bora Bora village '
            '(Vaitape), vue sur le mont Otemanu. Lit double, cuisine équipée, salle '
            'd\'eau, terrasse avec transat. Wifi fibre, eau chaude solaire, climatiseur. '
            'Toutes charges incluses dans le loyer. Idéal couple ou professionnel en '
            'mission. Disponible à partir du 1er avril. Caution 1 mois. '
            'Références locataires exigées.'
        ),
        'prix': 110000, 'prix_label': '110 000 XPF / mois tout inclus',
        'categorie': 'immobilier', 'sous_categorie': 'immo-appartements',
        'localisation': 'Bora Bora',
        'photos': [_photo('bungalow-mountain'), _photo('studio-furnished')],
    },
    {
        'titre': 'Cours de Tahitien — tous niveaux, Bora Bora & visio',
        'description': (
            'Professeur natif de Bora Bora, enseignement du reo Māohi depuis 10 ans. '
            'Cours individuels ou en petit groupe (max 4). Programme sur-mesure : '
            'communication quotidienne, culture et traditions polynésiennes, préparation '
            'au brevet de tahitien. Cours en présentiel à Bora Bora ou en visioconférence '
            'pour toute la Polynésie. Matériel pédagogique fourni. '
            '1ère leçon d\'essai offerte.'
        ),
        'prix': 2000, 'prix_label': '2 000 XPF / heure',
        'categorie': 'services', 'sous_categorie': 'services-cours',
        'localisation': 'Bora Bora',
        'photos': [_photo('polynesian-culture'), _photo('language-class')],
    },

    # ── Teva Paruru ───────────────────────────────────────────────────────────
    {
        'titre': 'Climatiseur Daikin 18 000 BTU — split mural, 2022',
        'description': (
            'Climatiseur Daikin Perfera FTXM50R split mural 18 000 BTU, installé en 2022. '
            'Entretien annuel effectué (filtres nettoyés, gaz vérifié). '
            'Froid très rapide, silencieux (19dB intérieur). Télécommande Daikin et '
            'application smartphone incluses. Vendu avec unité extérieure. '
            'Démontage et transport à la charge de l\'acheteur. '
            'Idéal pour pièce de 30–40m².'
        ),
        'prix': 90000, 'categorie': 'electronique', 'sous_categorie': 'elec-electromenager',
        'localisation': 'Papeete',
        'photos': [_photo('aircon-split'), _photo('modern-interior-cool')],
    },
    {
        'titre': 'Transport & déménagement — camion 3,5T Tahiti entier',
        'description': (
            'Paruru Transport — spécialiste déménagement et livraison sur tout Tahiti. '
            'Camion 20m³ avec sangles et couvertures de protection. '
            'Équipe de 2 personnes disponible 7j/7, y compris jours fériés. '
            'Forfait déménagement studio à partir de 25 000 XPF. '
            'Livraison matériaux, mobilier, électroménager. Tarif à l\'heure possible. '
            'Devis gratuit par WhatsApp sous 2h. Assurance RC pro incluse.'
        ),
        'prix': 8000, 'prix_label': '8 000 XPF / heure (mini 2h)',
        'categorie': 'services', 'sous_categorie': 'services-transport',
        'localisation': 'Papeete',
        'photos': [_photo('moving-truck'), _photo('delivery-vehicle')],
    },

    # ── Anani Tupaia ──────────────────────────────────────────────────────────
    {
        'titre': 'Bateau de pêche 6m — moteur Yamaha 115CV 4T',
        'description': (
            'Bateau coque fibre 6 mètres, moteur Yamaha F115 4 temps injection (2019), '
            '245 heures moteur. Équipé : sonar couleur Garmin, VHF marine, bimini, '
            'glacière 50L, porte-cannes ×6, ancre + mouillage. Remorque galva incluse. '
            'Entretien régulier chez Yamaha Marine Raiatea. '
            'Parfait pour pêche au gros ou balade avec famille. '
            'Vente cause départ en métropole.'
        ),
        'prix': 950000, 'categorie': 'vehicules', 'sous_categorie': 'vehicules-bateaux',
        'localisation': 'Raiatea',
        'photos': [_photo('fishing-boat'), _photo('ocean-boat-pacific')],
    },
    {
        'titre': 'TV Samsung 65" Neo QLED 4K — QN85B, 2023',
        'description': (
            'TV Samsung 65 pouces Neo QLED 4K QN85B, achetée en juillet 2023. '
            '144Hz natif, HDMI 2.1, VRR & AMD FreeSync Premium Pro (idéal gaming). '
            'Dolby Atmos, Tizen OS avec Netflix/Disney+/Prime préinstallés. '
            'Image brillante, noirs profonds. En parfait état, jamais déplacée. '
            'Fixation murale Samsung offerte. Vente cause achat TV OLED. '
            'À enlever à Raiatea, possibilité envoi maritime inter-îles.'
        ),
        'prix': 85000, 'categorie': 'electronique', 'sous_categorie': 'elec-tv',
        'localisation': 'Raiatea',
        'photos': [_photo('samsung-qled-tv'), _photo('living-room-tv')],
    },

    # ── Moana Tetuanui ────────────────────────────────────────────────────────
    {
        'titre': 'Tenue traditionnelle Heiva — pareu soie, T.42/44',
        'description': (
            'Magnifique tenue traditionnelle polynésienne confectionnée pour le Heiva 2024. '
            'Pareu en soie naturelle imprimée, motifs tiare et raie manta, couleurs '
            'bordeaux et or. Taille 42/44. Jamais revendu depuis le spectacle. '
            'Broderies faites à la main, tête de fleurs incluse. '
            'Également disponible : pareu coordonné pour homme (offert si achat ensemble). '
            'Nettoyage à sec recommandé. Photos supplémentaires sur demande.'
        ),
        'prix': 12000, 'categorie': 'autres', 'sous_categorie': 'autres-vetements',
        'localisation': 'Tahaa',
        'photos': [_photo('polynesian-dress'), _photo('traditional-fabric')],
    },
    {
        'titre': 'Poussette Bugaboo Fox 3 — bleu nuit + accessoires',
        'description': (
            'Poussette Bugaboo Fox 3 complète, coloris bleu nuit / châssis noir. '
            'Utilisée 18 mois, parfait état. Inclus dans la vente : nacelle nouveau-né, '
            'siège évolutif, tablette parent, sac à langer Bugaboo, protection pluie, '
            'habillage soleil. Pneus en bon état (pas de crevaison). '
            'Notice et garantie constructeur. Bugaboo coûte 180 000 XPF neuf. '
            'Vente cause enfant trop grand. À venir chercher à Tahaa.'
        ),
        'prix': 78000, 'categorie': 'autres', 'sous_categorie': 'autres-puericulture',
        'localisation': 'Tahaa',
        'photos': [_photo('bugaboo-stroller'), _photo('baby-carriage')],
    },
]


class Command(BaseCommand):
    help = 'Crée 10 utilisateurs démo + 20 annonces avec photos pour remplir le site'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Supprime les comptes @demo.pf et leurs annonces avant de les recréer'
        )

    def handle(self, *args, **options):
        if options['reset']:
            deleted_users = User.objects.filter(email__endswith='@demo.pf').count()
            User.objects.filter(email__endswith='@demo.pf').delete()
            self.stdout.write(self.style.WARNING(
                f'  {deleted_users} utilisateurs @demo.pf supprimés (annonces supprimées en cascade).'
            ))

        created_users = 0
        created_annonces = 0

        for i, u_data in enumerate(DEMO_USERS):
            user, created = User.objects.get_or_create(
                email=u_data['email'],
                defaults={
                    'nom':           u_data['nom'],
                    'tel':           u_data.get('tel', ''),
                    'role':          u_data.get('role', 'personnel'),
                    'nom_entreprise': u_data.get('entreprise', ''),
                    'is_active':     True,
                }
            )
            if created:
                user.set_password('demo_tbg_2025!')
                user.save()
                created_users += 1
                self.stdout.write(f'  + Utilisateur : {u_data["nom"]} ({u_data["email"]})')
            else:
                self.stdout.write(f'  ~ Existant   : {u_data["nom"]}')

            # 2 annonces par utilisateur
            for annonce_data in DEMO_ANNONCES[i * 2: i * 2 + 2]:
                if Annonce.objects.filter(
                    user=user, titre=annonce_data['titre']
                ).exists():
                    self.stdout.write(f'      ~ Annonce déjà existante : {annonce_data["titre"][:50]}')
                    continue

                Annonce.objects.create(
                    user=user,
                    titre=annonce_data['titre'],
                    description=annonce_data['description'],
                    prix=annonce_data.get('prix', 0),
                    prix_label=annonce_data.get('prix_label', ''),
                    categorie=annonce_data['categorie'],
                    sous_categorie=annonce_data.get('sous_categorie', ''),
                    localisation=annonce_data.get('localisation', 'Papeete'),
                    photos=annonce_data.get('photos', []),
                    statut='actif',
                    boost=(i % 3 == 0),  # 1 annonce sur 3 est boostée
                )
                created_annonces += 1
                self.stdout.write(
                    f'      + Annonce : {annonce_data["titre"][:55]}...'
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] {created_users} utilisateurs et {created_annonces} annonces créés.'
        ))
        self.stdout.write(
            '  Mot de passe de tous les comptes démo : demo_tbg_2025!\n'
            '  Pour tout supprimer : python manage.py seed_demo_users --reset\n'
        )
