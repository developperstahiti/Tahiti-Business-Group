"""
Management command : python manage.py seed_annonces
Crée ~15 annonces factices par catégorie pour tester le rendu du site.
Supprime les annonces factices existantes avant de les recréer (--reset).
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ads.models import Annonce

User = get_user_model()

LOCALISATIONS = [
    'Papeete', 'Faa\'a', 'Punaauia', 'Pirae', 'Arue', 'Mahina',
    'Papara', 'Moorea', 'Taravao', 'Paea', 'Bora Bora', 'Raiatea',
    'Huahine', 'Rangiroa', 'Nuku Hiva',
]

SEED_TAG = '[SEED]'  # tag pour identifier les annonces factices

DATA = {
    'vehicules': [
        {'titre': 'Toyota Hilux 2020 — 4x4 diesel très bon état',
         'desc': 'Hilux double cabine, 85 000 km, boîte auto, climatisation, sellerie cuir. Carnet d\'entretien complet. Révisé en octobre 2024.',
         'prix': 3200000, 'sous': 'vehicules-4x4'},
        {'titre': 'Honda CRV 2018 — essence, faible kilométrage',
         'desc': '62 000 km, 1 seul propriétaire, toutes options. Idéal famille. CT valide 2026. Disponible immédiatement.',
         'prix': 2450000, 'sous': 'vehicules-4x4'},
        {'titre': 'Nissan Navara 2019 double cab — diesel',
         'desc': 'Kilométrage 110 000 km, benne utilitaire, attelage 3.5t, caméra de recul. Très bon état général.',
         'prix': 2800000, 'sous': 'vehicules-4x4'},
        {'titre': 'Mitsubishi Pajero 2017 — 4x4 7 places',
         'desc': '7 places, toit ouvrant, 130 000 km, GPS, écran tactile. Quelques rayures légères. Prix à débattre.',
         'prix': 2600000, 'sous': 'vehicules-4x4'},
        {'titre': 'Ford Ranger Wildtrak 2021 — quasi neuf',
         'desc': '38 000 km seulement, full options, barre de toit, bullbar. Comme neuf. Première main.',
         'prix': 3800000, 'sous': 'vehicules-4x4'},
        {'titre': 'Scooter Yamaha NMAX 155 — 2022 bleu',
         'desc': '12 000 km, freins ABS, coffre topcase inclus, très bien entretenu. Parfait pour Papeete.',
         'prix': 280000, 'sous': 'vehicules-2roues'},
        {'titre': 'Honda PCX 125 — 2021 excellent état',
         'desc': '9 500 km, permis A1, couleur grise, pneus neufs, contrôle technique valide.',
         'prix': 220000, 'sous': 'vehicules-2roues'},
        {'titre': 'Moto Kawasaki Z400 — 2020 avec équipements',
         'desc': '18 000 km, casque et gants inclus. Révision faite. Idéal pour débutant ou intermédiaire.',
         'prix': 450000, 'sous': 'vehicules-2roues'},
        {'titre': 'Bateau Quicksilver 500 — moteur Yamaha 60CV',
         'desc': 'Pêche et balade, bimini, sonar, VHF marine. Remorque incluse. Propulseur en très bon état.',
         'prix': 1800000, 'sous': 'vehicules-bateaux'},
        {'titre': 'Jet-ski Sea-Doo Spark 90CV — 2022',
         'desc': '45 heures moteur, housse de transport, gilets inclus. Couleur orange. Rangé sous abri.',
         'prix': 950000, 'sous': 'vehicules-bateaux'},
        {'titre': 'Camion benne Isuzu 2016 — 3.5t',
         'desc': '180 000 km, benne 6m3, hayons hydrauliques, poids lourd léger. Idéal artisan.',
         'prix': 1500000, 'sous': 'vehicules-utilitaires'},
        {'titre': 'Peugeot Partner L2 2019 — frigo frigorifique',
         'desc': '90 000 km, cellule frigorifique professionnelle, parfait état, immatriculé Polynésie.',
         'prix': 1200000, 'sous': 'vehicules-utilitaires'},
        {'titre': 'Pneus 265/70R17 tout terrain — lot de 4',
         'desc': 'Bridgestone Dueler AT 694, très peu usés (2 saisons), vendus avec jantes Toyota Hilux.',
         'prix': 85000, 'sous': 'vehicules-pieces'},
        {'titre': 'Jantes aluminium 17" Toyota — 5 trous',
         'desc': 'Jantes sport noires 17 pouces, compatibles Hilux/Fortuner/Land Cruiser. État 9/10.',
         'prix': 55000, 'sous': 'vehicules-pieces'},
        {'titre': 'Kit suspension rehaussé +5cm — Nissan Navara',
         'desc': 'Kit complet amortisseurs et ressorts, jamais posé, dans emballage d\'origine.',
         'prix': 65000, 'sous': 'vehicules-pieces'},
    ],

    'immobilier': [
        {'titre': 'Appartement F3 55m² — Papeete centre, vue mer',
         'desc': 'Séjour lumineux, 2 chambres, cuisine équipée, parking privé. Proche marché de Papeete. Disponible mars 2025.',
         'prix': 120000, 'prix_label': '120 000 XPF/mois', 'sous': 'immo-appartements'},
        {'titre': 'Studio meublé 28m² — Faa\'a, proche aéroport',
         'desc': 'Tout inclus : meublé, électroménager, wifi. Idéal pour déplacement professionnel. Caution 1 mois.',
         'prix': 75000, 'prix_label': '75 000 XPF/mois', 'sous': 'immo-appartements'},
        {'titre': 'Appartement F2 42m² — Punaauia bord de mer',
         'desc': 'Vue lagon, terrasse 10m², parking, gardien. Résidence sécurisée avec piscine.',
         'prix': 145000, 'prix_label': '145 000 XPF/mois', 'sous': 'immo-appartements'},
        {'titre': 'Appartement F4 80m² — Pirae, calme et lumineux',
         'desc': '3 chambres, grande cuisine, 2 SDB, 2 parkings souterrains. Proche toutes commodités.',
         'prix': 165000, 'prix_label': '165 000 XPF/mois', 'sous': 'immo-appartements'},
        {'titre': 'Villa F5 150m² — Paea, terrain 800m², piscine',
         'desc': '4 chambres, salon cathédrale, piscine 8x4m, carport 3 voitures. Vue montagne magnifique.',
         'prix': 55000000, 'sous': 'immo-maisons'},
        {'titre': 'Maison F4 — Mahina, terrain plat 600m²',
         'desc': 'Plain-pied, cuisine ouverte, 3 chambres, bureau, fenua plat et plat. Idéal famille.',
         'prix': 38000000, 'sous': 'immo-maisons'},
        {'titre': 'Bungalow bois 90m² — Moorea Maharepa',
         'desc': 'Vue montagne, jardin tropical, terrasse couverte. Maison de charme en bois de qualité.',
         'prix': 42000000, 'sous': 'immo-maisons'},
        {'titre': 'Terrain 1 200m² viabilisé — Papara bord de route',
         'desc': 'Terrain plat, eau + électricité en limite, accès direct RN1. Permis de construire faisable.',
         'prix': 12000000, 'sous': 'immo-terrains'},
        {'titre': 'Terrain agricole 5 000m² — Taravao plateau',
         'desc': 'Idéal élevage ou culture maraîchère. Source d\'eau naturelle. Vue panoramique sur les deux presqu\'îles.',
         'prix': 8500000, 'sous': 'immo-terrains'},
        {'titre': 'Local commercial 80m² — Papeete hypercentre',
         'desc': 'RDC, vitrine, 3 pièces + réserve + WC. Idéal restaurant, boutique ou bureau. Bail commercial.',
         'prix': 180000, 'prix_label': '180 000 XPF/mois', 'sous': 'immo-bureaux'},
        {'titre': 'Bureau 40m² — immeuble Fare Tony Papeete',
         'desc': '2 pièces cloisonnées, climatisé, parking inclus. Immeuble professionnel sécurisé.',
         'prix': 95000, 'prix_label': '95 000 XPF/mois', 'sous': 'immo-bureaux'},
        {'titre': 'Bungalow vacances Bora Bora — 2 pers, piscine',
         'desc': 'Accès plage privée, vue sur le lagon et Otemanu. Climatisé, wifi haut débit. 3 nuits min.',
         'prix': 35000, 'prix_label': '35 000 XPF/nuit', 'sous': 'immo-saisonnieres'},
        {'titre': 'Studio saisonnier Moorea — 4 pers, vue lagon',
         'desc': 'Coco Palm Résidence, terrasse avec hamac, kayak inclus, proche restaurants.',
         'prix': 18000, 'prix_label': '18 000 XPF/nuit', 'sous': 'immo-saisonnieres'},
        {'titre': 'Parking couvert — Papeete centre, sécurisé',
         'desc': 'Porte télécommandée, caméra 24h/24. Idéal voiture ou moto. Proche Mairie.',
         'prix': 18000, 'prix_label': '18 000 XPF/mois', 'sous': 'immo-parkings'},
        {'titre': 'Garage fermé 20m² — Faa\'a, stockage ou véhicule',
         'desc': 'Grande hauteur 2.5m, portail électrique. Idéal camping-car, bateau ou stockage pro.',
         'prix': 25000, 'prix_label': '25 000 XPF/mois', 'sous': 'immo-parkings'},
    ],

    'electronique': [
        {'titre': 'iPhone 15 Pro 256Go — état parfait, noir',
         'desc': 'Acheté en décembre 2024, encore sous garantie Apple. Toujours avec coque et protection d\'écran. Boîte d\'origine.',
         'prix': 145000, 'sous': 'elec-telephones'},
        {'titre': 'Samsung Galaxy S23 Ultra 512Go — bleu',
         'desc': 'S-Pen inclus, 100W de charge, 200Mp photo. Très peu utilisé, comme neuf. Débloqué tout opérateur.',
         'prix': 125000, 'sous': 'elec-telephones'},
        {'titre': 'iPhone 13 128Go — excellent état, rouge',
         'desc': '5G, Face ID, autonomie excellente. Légers signes d\'usure invisibles. Accessoires inclus.',
         'prix': 75000, 'sous': 'elec-telephones'},
        {'titre': 'Google Pixel 8 Pro 256Go — neuf sous blister',
         'desc': 'Jamais ouvert, acheté en France. Garantie constructeur 1 an. Tous accessoires inclus.',
         'prix': 110000, 'sous': 'elec-telephones'},
        {'titre': 'MacBook Pro M3 14" 16Go/512Go — 2024',
         'desc': 'Acheté en janvier 2025, 2 mois d\'utilisation. Puce M3 ultra-rapide. Autonomie 18h. Parfait état.',
         'prix': 320000, 'sous': 'elec-ordinateurs'},
        {'titre': 'iPad Pro 12.9" M2 256Go Wifi — gris sidéral',
         'desc': 'Apple Pencil 2e gen inclus, Magic Keyboard inclus. Parfait pour artistes et professionnels.',
         'prix': 185000, 'sous': 'elec-ordinateurs'},
        {'titre': 'PC Gamer Asus ROG — RTX 4070, i7 13e gen',
         'desc': '32Go RAM DDR5, SSD 1To NVMe, écran 165Hz 27". Jeux 4K fluides. Peu utilisé, état neuf.',
         'prix': 280000, 'sous': 'elec-pc'},
        {'titre': 'Dell XPS 15 — i9, 32Go, RTX 4060',
         'desc': 'Écran OLED 3.5K, SSD 1To, batterie 6h en utilisation intensive. Parfait état, sac inclus.',
         'prix': 265000, 'sous': 'elec-pc'},
        {'titre': 'TV LG OLED 65" 4K — C3 série 2023',
         'desc': 'Dalle OLED evo, 120Hz, Dolby Vision & Atmos, webOS. Image de référence. Jamais transporté.',
         'prix': 220000, 'sous': 'elec-tv'},
        {'titre': 'Barre de son Sony HT-A7000 — Dolby Atmos',
         'desc': '500W, 7.1.2ch Atmos & DTS:X, Bluetooth, HDMI eARC. Parfait état, télécommande incluse.',
         'prix': 75000, 'sous': 'elec-tv'},
        {'titre': 'PS5 Standard + 2 manettes + 5 jeux',
         'desc': 'Console + DualSense blanc + DualSense noir + FIFA 25, Spider-Man 2, God of War Ragnarök...',
         'prix': 95000, 'sous': 'elec-jeux'},
        {'titre': 'Nintendo Switch OLED — blanc, très bon état',
         'desc': 'Zelda Tears of the Kingdom + Mario Kart 8 + Pokémon Ecarlate inclus. Accessoires complets.',
         'prix': 55000, 'sous': 'elec-jeux'},
        {'titre': 'Lave-linge Samsung 9kg — inverter A+++',
         'desc': '1400 tours, moteur inverter silencieux, 3 ans d\'utilisation, aucun problème. Livraison possible.',
         'prix': 65000, 'sous': 'elec-electromenager'},
        {'titre': 'Réfrigérateur LG 450L No Frost — inox',
         'desc': 'Congélateur bas, distributeur eau, très bon état, déménagement forcé. À enlever rapidement.',
         'prix': 55000, 'sous': 'elec-electromenager'},
        {'titre': 'Climatiseur Daikin 18000 BTU — split mural',
         'desc': 'Posé en 2022, entretenu régulièrement, télécommande, froid rapide. Démontage par acheteur.',
         'prix': 85000, 'sous': 'elec-electromenager'},
    ],

    'emploi': [
        {'titre': 'Commercial(e) B2B — secteur téléphonie & services',
         'desc': 'CDI, fixe + commissions attractives. Expérience vente B2B requise. Véhicule de service fourni. Secteur : Papeete / Faa\'a.',
         'prix': 0, 'prix_label': 'À partir de 200 000 XPF/mois', 'sous': 'emploi-commerciaux'},
        {'titre': 'Responsable commercial(e) — agence immobilière',
         'desc': 'CDI, commission 5% sur ventes. Permis B requis. Portfolio clients existant. Objectif : 2 ventes/mois.',
         'prix': 0, 'prix_label': 'Commission sur ventes', 'sous': 'emploi-commerciaux'},
        {'titre': 'Développeur web Django/Python — CDI Papeete',
         'desc': '3 ans d\'expérience minimum, Django REST, PostgreSQL, déploiement Linux/Railway. Télétravail partiel possible.',
         'prix': 0, 'prix_label': '300 000 – 400 000 XPF/mois', 'sous': 'emploi-informatique'},
        {'titre': 'Technicien réseau & systèmes — IT Support',
         'desc': 'Expérience Cisco, Windows Server, Active Directory. Itinérant chez clients professionnels. CDD 6 mois renouvelable.',
         'prix': 0, 'prix_label': '250 000 XPF/mois', 'sous': 'emploi-informatique'},
        {'titre': 'Chef de rang — restaurant gastronomique Papeete',
         'desc': 'CDI, service soir uniquement, 2 jours de repos consécutifs. Expérience fine dining exigée. Pourboires conséquents.',
         'prix': 0, 'prix_label': '180 000 XPF/mois + tips', 'sous': 'emploi-hotellerie'},
        {'titre': 'Réceptionniste bilingue — hôtel 4 étoiles Moorea',
         'desc': 'Anglais courant obligatoire, logé-nourri, 2 jours off/semaine. CDD 6 mois avec possibilité CDI.',
         'prix': 0, 'prix_label': 'Logé + 160 000 XPF/mois', 'sous': 'emploi-hotellerie'},
        {'titre': 'Cuisinier(ère) confirmé(e) — snack brasserie Faa\'a',
         'desc': 'Pizzas, poisson cru, plats tahitiens. Mi-temps possible. Horaires aménageables. Débutant accepté avec formation.',
         'prix': 0, 'prix_label': '150 000 XPF/mois', 'sous': 'emploi-hotellerie'},
        {'titre': 'Chef de chantier — construction villas Moorea',
         'desc': 'Gestion équipe 8 ouvriers, lecture plans, coordination sous-traitants. CDI, véhicule de chantier fourni.',
         'prix': 0, 'prix_label': '350 000 XPF/mois', 'sous': 'emploi-btp'},
        {'titre': 'Électricien qualificé — chantiers résidentiels',
         'desc': 'Habilitation B2V H0V exigée, expérience 3 ans min. CDI, prime outillage, panier repas.',
         'prix': 0, 'prix_label': '220 000 XPF/mois', 'sous': 'emploi-btp'},
        {'titre': 'Plombier-chauffagiste — entreprise artisanale',
         'desc': 'Dépannage + chantiers neufs, clientèle fidèle, véhicule atelier fourni. Autonome et sérieux.',
         'prix': 0, 'prix_label': '200 000 XPF/mois', 'sous': 'emploi-btp'},
        {'titre': 'Aide à domicile — personnes âgées Papeete',
         'desc': 'Mi-temps ou plein temps, matin 7h-12h. Accompagnement, ménage, courses. Permis B requis. Débutant accepté.',
         'prix': 0, 'prix_label': '130 000 XPF/mois', 'sous': 'emploi-services'},
        {'titre': 'Agent de sécurité — centre commercial Punaauia',
         'desc': 'Carte pro obligatoire, horaires tournants, prime nuit. CDI temps plein.',
         'prix': 0, 'prix_label': '170 000 XPF/mois + primes', 'sous': 'emploi-services'},
        {'titre': 'Chauffeur livreur — e-commerce local',
         'desc': 'Livraison colis zone Tahiti, véhicule fourni, smartphone professionnel. CDI, départ Taravao.',
         'prix': 0, 'prix_label': '160 000 XPF/mois', 'sous': 'emploi-services'},
        {'titre': 'Secrétaire médicale — cabinet médical Pirae',
         'desc': 'Accueil patients, prise de RDV, facturation CPS. Mi-temps 20h/semaine. Expérience souhaitée.',
         'prix': 0, 'prix_label': '100 000 XPF/mois', 'sous': 'emploi-services'},
        {'titre': 'Commercial(e) assurance — Axa Polynésie',
         'desc': 'Prospection terrain + gestion portefeuille clients. Formation interne assurée. Rémunération déplafonnée.',
         'prix': 0, 'prix_label': 'Fixe + commissions illimitées', 'sous': 'emploi-commerciaux'},
    ],

    'services': [
        {'titre': 'Peinture intérieure / extérieure — devis gratuit',
         'desc': 'Artisan peintre 15 ans d\'expérience, travail soigné, fournitures incluses sur devis. Références disponibles. Tahiti entier.',
         'prix': 0, 'prix_label': 'Sur devis', 'sous': 'services-travaux'},
        {'titre': 'Maçonnerie — construction fondations et dalles',
         'desc': 'Entreprise locale, assurée, décennale. Constructions neuves et rénovation. Délais respectés.',
         'prix': 0, 'prix_label': 'Sur devis', 'sous': 'services-travaux'},
        {'titre': 'Pose de climatisation — Daikin agréé',
         'desc': 'Installateur certifié, intervention rapide. Entretien annuel disponible. Garantie 2 ans pièces + main d\'œuvre.',
         'prix': 35000, 'prix_label': 'À partir de 35 000 XPF', 'sous': 'services-travaux'},
        {'titre': 'Carrelage & faïence — salle de bain et cuisine',
         'desc': 'Pose sur chape neuve ou rénovation. Joints époxy disponibles. Déplacement gratuit pour devis.',
         'prix': 0, 'prix_label': 'Sur devis', 'sous': 'services-travaux'},
        {'titre': 'Cours particuliers maths / physique — lycée & prépa',
         'desc': 'Ingénieur diplômé, 8 ans d\'expérience. Résultats garantis ou remboursé. À domicile ou en ligne.',
         'prix': 3000, 'prix_label': '3 000 XPF/heure', 'sous': 'services-cours'},
        {'titre': 'Cours de tahitien — tous niveaux',
         'desc': 'Professeur natif, langue et culture. Cours individuels ou en groupe (max 4). Papeete et visio.',
         'prix': 2500, 'prix_label': '2 500 XPF/heure', 'sous': 'services-cours'},
        {'titre': 'Formation bureautique — Word, Excel, PowerPoint',
         'desc': 'Formateur certifié Microsoft, groupes de 2 à 6 personnes. Intra-entreprise possible.',
         'prix': 5000, 'prix_label': '5 000 XPF/session', 'sous': 'services-cours'},
        {'titre': 'Transport de marchandises — camion 3.5T Tahiti',
         'desc': 'Déménagement, livraison matériaux, transfert mobilier. Disponible 7j/7. Tarif à l\'heure ou au forfait.',
         'prix': 8000, 'prix_label': '8 000 XPF/heure', 'sous': 'services-transport'},
        {'titre': 'Taxi agréé — navettes aéroport Faa\'a 24h/24',
         'desc': 'Véhicule climatisé, ponctuel, réservation WhatsApp. Tarifs fixes. 89 XX XX XX.',
         'prix': 3500, 'prix_label': 'À partir de 3 500 XPF', 'sous': 'services-transport'},
        {'titre': 'Coiffure à domicile — femme & homme Papeete',
         'desc': 'Coupe, couleur, lissage brésilien. Matériel professionnel. Sur rendez-vous. Papeete, Pirae, Arue.',
         'prix': 4000, 'prix_label': 'Coupe à partir de 4 000 XPF', 'sous': 'services-sante'},
        {'titre': 'Massage relaxant / sportif — praticienne diplômée',
         'desc': 'Massage suédois, thaï et sportif. Cabinet ou domicile. Réservation 48h. Bora Bora et Tahiti.',
         'prix': 6000, 'prix_label': '6 000 XPF / 60 min', 'sous': 'services-sante'},
        {'titre': 'Manucure gel & pose d\'ongles — salon Punaauia',
         'desc': 'Shellac, semi-permanent, extensions. Sur rendez-vous uniquement. Instagram : @nailstahiti.',
         'prix': 5500, 'prix_label': 'À partir de 5 500 XPF', 'sous': 'services-sante'},
        {'titre': 'Entretien jardin — tonte, taille, nettoyage',
         'desc': 'Jardinier professionnel, passage hebdomadaire ou mensuel. Devis gratuit sur place. Tahiti + Moorea.',
         'prix': 0, 'prix_label': 'Sur devis', 'sous': 'services-jardinage'},
        {'titre': 'Création jardin tropical — plantation & aménagement',
         'desc': 'Paysagiste diplômé, conception d\'espaces verts, choix plantes endémiques. Tahiti entier.',
         'prix': 0, 'prix_label': 'Sur devis', 'sous': 'services-jardinage'},
        {'titre': 'Nettoyage de toiture & gouttières — professionnel',
         'desc': 'Démoussage, traitement anti-mousse, réparation petites fuites. Assurance RC pro. Devis gratuit.',
         'prix': 0, 'prix_label': 'Sur devis', 'sous': 'services-travaux'},
    ],

    'autres': [
        {'titre': 'Canapé d\'angle cuir noir 5 places — excellent état',
         'desc': 'Canapé convertible, méridienne gauche, coffre de rangement. 2 ans d\'utilisation. Non fumeur.',
         'prix': 85000, 'sous': 'autres-meubles'},
        {'titre': 'Table à manger bois massif + 6 chaises',
         'desc': 'Bois de teck, table extensible 140-180cm. Chaises tissu gris anthracite. Très bon état.',
         'prix': 65000, 'sous': 'autres-meubles'},
        {'titre': 'Lit King Size 180x200 + matelas Simmons',
         'desc': 'Sommier à lattes, têtière en cuir marron, matelas à ressorts ensachés. Comme neuf.',
         'prix': 95000, 'sous': 'autres-meubles'},
        {'titre': 'Bibliothèque sur-mesure bois blanc — IKEA pro',
         'desc': 'Kallax 5x4 modules, 2m x 1.60m, avec portes et tiroirs. Démonté et emballé. À enlever.',
         'prix': 25000, 'sous': 'autres-meubles'},
        {'titre': 'Lot vêtements femme T.38/40 — marques',
         'desc': 'Zara, H&M, Mango — robes, tops, jeans. Une dizaine de pièces. Très bon état. Photos sur demande.',
         'prix': 8000, 'sous': 'autres-vetements'},
        {'titre': 'Vêtements bébé 0-6 mois — lot complet',
         'desc': '50+ pièces : bodies, pyjamas, grenouillères, chaussons. Garçon. Propres, non tachés.',
         'prix': 5000, 'sous': 'autres-vetements'},
        {'titre': 'Tenue traditionnelle polynésienne — pareu soie',
         'desc': 'Pareu Heiva, couleurs rouge et or, T.42/44. Jamais porté après spectacle. Avec pareo hommes.',
         'prix': 12000, 'sous': 'autres-vetements'},
        {'titre': 'Vélo VTT Scott Aspect 950 — 29 pouces',
         'desc': '27 vitesses, freins hydrauliques Shimano, fourche suspendue. 2 ans, bon état, pneus neufs.',
         'prix': 55000, 'sous': 'autres-sport'},
        {'titre': 'Kayak de mer Sevylor — 2 places gonflable',
         'desc': 'Pagaies incluses, pompe et sac de transport. Peu utilisé. Parfait pour le lagon.',
         'prix': 28000, 'sous': 'autres-sport'},
        {'titre': 'Matériel de surf complet — planche 7\'2 + combinaison',
         'desc': 'Planche Firewire + combinaison O\'Neill 3/2mm T.L + leash + pad. Idéal débutant/intermédiaire.',
         'prix': 35000, 'sous': 'autres-sport'},
        {'titre': 'Poussette Bugaboo Fox 3 — bleu nuit',
         'desc': 'Nacelle + siège, tablette parent, sac fourre-tout. 18 mois d\'utilisation. Parfait état.',
         'prix': 85000, 'sous': 'autres-puericulture'},
        {'titre': 'Lit bébé évolutif + matelas + parure',
         'desc': 'Lit 60x120 évolutif jusqu\'à 90x190, barrières, tiroir. Coloris blanc chêne. Matelas neuf.',
         'prix': 35000, 'sous': 'autres-puericulture'},
        {'titre': 'Siège auto groupe 0+/1 Chicco — isofix',
         'desc': 'De 0 à 4 ans, isofix, rétrograde ou face à la route. Jamais accidenté. Notice disponible.',
         'prix': 18000, 'sous': 'autres-puericulture'},
        {'titre': 'Guitare acoustique Yamaha F310 + housse',
         'desc': 'Cordes neuves, accordeur clip inclus, cahier de partitions. Idéal pour débuter.',
         'prix': 15000, 'sous': 'autres-divers'},
        {'titre': 'Drone DJI Mini 3 Pro — kit fly more',
         'desc': 'Batteries x3, chargeur multi, sac, poids <249g (sans autorisation). 45 min de vol.',
         'prix': 95000, 'sous': 'autres-divers'},
    ],
}


class Command(BaseCommand):
    help = 'Peuple la base avec des annonces factices pour chaque catégorie'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Supprime les annonces [SEED] existantes avant de les recréer'
        )

    def handle(self, *args, **options):
        if options['reset']:
            deleted, _ = Annonce.objects.filter(titre__startswith=SEED_TAG).delete()
            self.stdout.write(self.style.WARNING(f'  {deleted} annonces [SEED] supprimées.'))

        # Récupérer ou créer un utilisateur factice
        seed_email = 'seed@tbg.pf'
        user, created = User.objects.get_or_create(
            email=seed_email,
            defaults={
                'nom': 'Vendeur TBG',
                'role': 'personnel',
                'is_active': True,
            }
        )
        if created:
            user.set_password('seed_password_tbg_2025')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'  Utilisateur seed créé : {seed_email}'))
        else:
            self.stdout.write(f'  Utilisateur seed existant : {seed_email}')

        locs = LOCALISATIONS
        total = 0

        for categorie, annonces in DATA.items():
            for i, a in enumerate(annonces):
                titre_seed = f"{SEED_TAG} {a['titre']}"
                # Éviter les doublons si --reset n'est pas utilisé
                if Annonce.objects.filter(titre=titre_seed).exists():
                    continue

                Annonce.objects.create(
                    user=user,
                    titre=titre_seed,
                    description=a['desc'],
                    prix=a.get('prix', random.randint(5000, 500000)),
                    prix_label=a.get('prix_label', ''),
                    categorie=categorie,
                    sous_categorie=a.get('sous', ''),
                    localisation=locs[i % len(locs)],
                    statut='actif',
                    views=random.randint(0, 200),
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] {total} annonces factices crees ({len(DATA)} categories x ~15 annonces).'
        ))
        self.stdout.write(
            '   Pour les supprimer : python manage.py seed_annonces --reset\n'
        )
