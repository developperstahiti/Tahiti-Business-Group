"""python manage.py seed_real_annonces — importe les vraies annonces TBG avec upload S3."""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ads.models import Annonce
from ads.image_utils import save_webp

BASE_IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), 'img')

ANNONCES = [
    {
        "titre": "Voiture hybride \u2014 Capture Hybride",
        "description": "Renault Capture hybride en excellent \u00e9tat. Faible kilom\u00e9trage, entretien suivi, premi\u00e8re main. Id\u00e9ale pour la ville et les longues distances.",
        "prix": 2900000, "prix_label": "",
        "categorie": "vehicules", "sous_categorie": "vehicules-4x4",
        "localisation": "Papeete",
        "images": ["capture hybride.jpg", "capture hybride 2.jpg"],
    },
    {
        "titre": "Citro\u00ebn C3 \u2014 Tr\u00e8s bon \u00e9tat",
        "description": "Citro\u00ebn C3 en tr\u00e8s bon \u00e9tat g\u00e9n\u00e9ral. Climatisation, faible consommation. Parfaite pour la ville de Papeete.",
        "prix": 1200000, "prix_label": "",
        "categorie": "vehicules", "sous_categorie": "vehicules-4x4",
        "localisation": "Faa'a",
        "images": ["citroen c3.jpg", "citroen c3 2.jpg", "citroen c3 3.jpg"],
    },
    {
        "titre": "DFM Joyear \u2014 Utilitaire",
        "description": "DFM Joyear utilitaire, id\u00e9al pour les professionnels. Cabine double, benne, robuste et \u00e9conomique.",
        "prix": 1800000, "prix_label": "",
        "categorie": "vehicules", "sous_categorie": "vehicules-utilitaires",
        "localisation": "Papeete",
        "images": ["dfm joyear.jpg"],
    },
    {
        "titre": "Renault Kadjar \u2014 SUV familial",
        "description": "Renault Kadjar SUV familial, finition Intens. GPS, cam\u00e9ra de recul, toit panoramique. Parfait \u00e9tat.",
        "prix": 2200000, "prix_label": "",
        "categorie": "vehicules", "sous_categorie": "vehicules-4x4",
        "localisation": "Pirae",
        "images": ["kadjar.jpg"],
    },
    {
        "titre": "PC Lenovo \u2014 Workstation Pro",
        "description": "PC Lenovo Workstation haute performance. Id\u00e9al pour le travail, le graphisme et le montage vid\u00e9o. \u00c9tat impeccable avec facture.",
        "prix": 450000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-pc",
        "localisation": "Papeete",
        "images": ["lenovo 1.jpg", "lenovo 2.jpg", "lenovo 3.jpg", "lenovo 4.jpg"],
    },
    {
        "titre": "Peugeot \u2014 Citadine \u00e9conomique",
        "description": "Peugeot en tr\u00e8s bon \u00e9tat, faible kilom\u00e9trage. Parfaite pour les d\u00e9placements quotidiens en ville. Entretien \u00e0 jour.",
        "prix": 950000, "prix_label": "",
        "categorie": "vehicules", "sous_categorie": "vehicules-4x4",
        "localisation": "Mahina",
        "images": ["peaugeot.jpg", "peaugeot 2.jpg"],
    },
    {
        "titre": "Air Fryer \u2014 Friteuse sans huile",
        "description": "Friteuse a air chaud, capacite 4L. Parfaite pour cuisiner sainement sans huile. Excellent etat, peu utilisee.",
        "prix": 15000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-electromenager",
        "localisation": "Papeete",
        "images": ["Air fryer.jpg"],
    },
    {
        "titre": "F2 a louer \u2014 Punaauia",
        "description": "Bel appartement F2 lumineux a Punaauia. Cuisine equipee, salle de bain, parking. Proche commerces et transports.",
        "prix": 75000, "prix_label": "",
        "categorie": "immobilier", "sous_categorie": "immo-appartements",
        "localisation": "Punaauia",
        "images": ["F2 punaauia.jpg", "F2 punaauia 2.jpg"],
    },
    {
        "titre": "Recherche Agent Commercial Immobilier",
        "description": "Agence immobiliere recrute agent commercial independant. Portefeuille clients existant, formation assuree. Remuneration a la commission attractive.",
        "prix": 0, "prix_label": "Commission",
        "categorie": "emploi", "sous_categorie": "emploi-commerciaux",
        "localisation": "Papeete",
        "images": ["agent commercial immo.jpg"],
    },
    {
        "titre": "Agent Immobilier \u2014 Offre emploi",
        "description": "Cabinet immobilier recherche agent immobilier experimente. CDI, salaire fixe + commissions. Gestion de biens residentiels et commerciaux en Polynesie.",
        "prix": 200000, "prix_label": "",
        "categorie": "emploi", "sous_categorie": "emploi-commerciaux",
        "localisation": "Papeete",
        "images": ["agent immo.jpg", "agent immo 2.jpg", "agent immo 3.jpg", "agent immo 4.jpg", "agent immo 5.jpg"],
    },
    {
        "titre": "Animateur Commercial \u2014 CDD",
        "description": "Entreprise recherche animateur commercial pour promotions en grande surface. CDD 3 mois renouvelable, dynamique et souriant(e) bienvenu(e).",
        "prix": 170000, "prix_label": "",
        "categorie": "emploi", "sous_categorie": "emploi-commerciaux",
        "localisation": "Papeete",
        "images": ["annimateur commercial.jpg"],
    },
    {
        "titre": "Appartement T3 \u2014 A louer Papeete",
        "description": "Grand appartement T3 en centre-ville de Papeete. Vue mer partielle, climatisation, securise. Proche de toutes commodites.",
        "prix": 95000, "prix_label": "",
        "categorie": "immobilier", "sous_categorie": "immo-appartements",
        "localisation": "Papeete",
        "images": ["appart 1.jpg", "appart 2.jpg", "appart 3.jpg", "appart 4.jpg", "appart 5.jpg"],
    },
    {
        "titre": "Appartement F2 \u2014 Location meublee",
        "description": "F2 entierement meuble et equipe, ideal pour une personne ou un couple. Calme, lumineux, acces rapide au centre.",
        "prix": 80000, "prix_label": "",
        "categorie": "immobilier", "sous_categorie": "immo-appartements",
        "localisation": "Papeete",
        "images": ["appart F2.jpg", "appart F2 2.jpg", "appart F2 3.jpg", "appart F2 4.jpg", "appart F2 5.jpg"],
    },
    {
        "titre": "Canap\u00e9 convertible \u2014 Tr\u00e8s bon \u00e9tat",
        "description": "Canap\u00e9 3 places convertible en lit, tissu gris chin\u00e9. M\u00e9canisme fluide, couchage confortable. Peu utilis\u00e9.",
        "prix": 35000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-meubles",
        "localisation": "Papeete",
        "images": ["canap\u00e9 convertible.jpg"],
    },
    {
        "titre": "Canap\u00e9 d'angle \u2014 Simili cuir",
        "description": "Grand canap\u00e9 d'angle en simili cuir noir, 5 places. Confortable et en bon \u00e9tat. Id\u00e9al pour grand salon.",
        "prix": 55000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-meubles",
        "localisation": "Faa'a",
        "images": ["canap\u00e9.jpg"],
    },
    {
        "titre": "Lot de 4 chaises salle \u00e0 manger",
        "description": "Lot de 4 chaises design pour salle \u00e0 manger. Structure m\u00e9tal, assise rembourr\u00e9e. Prix pour le lot complet.",
        "prix": 12000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-meubles",
        "localisation": "Papeete",
        "images": ["chaises.jpg"],
    },
    {
        "titre": "Conseiller Immobilier \u2014 CDI",
        "description": "Agence immobili\u00e8re de renom recrute conseiller immobilier confirm\u00e9. Gestion portefeuille clients, prospection, visites. V\u00e9hicule de service fourni.",
        "prix": 220000, "prix_label": "",
        "categorie": "emploi", "sous_categorie": "emploi-commerciaux",
        "localisation": "Papeete",
        "images": ["conseiller immo.jpg"],
    },
    {
        "titre": "iPad Air \u2014 Comme neuf 256 Go",
        "description": "iPad Air 5e g\u00e9n\u00e9ration, 256 Go, WiFi + Cellular. Tr\u00e8s peu utilis\u00e9, vendu avec chargeur et \u00e9tui de protection.",
        "prix": 85000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-ordinateurs",
        "localisation": "Papeete",
        "images": ["ipad air.jpg", "ipad air 2.jpg"],
    },
    {
        "titre": "Lot 2 vasques \u00e0 poser \u2014 Neuves",
        "description": "Lot de 2 vasques rondes \u00e0 poser, c\u00e9ramique blanche. Diam\u00e8tre 40cm. Jamais install\u00e9es, encore dans leur emballage.",
        "prix": 18000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-divers",
        "localisation": "Papeete",
        "images": ["lot 2 vasques.jpg"],
    },
    {
        "titre": "PC Gamer \u2014 RTX 4090 / 64 Go DDR5",
        "description": "PC gaming haut de gamme : RTX 4090, 64 Go DDR5, SSD NVMe 2 To. Watercooling AIO 360mm. Performances exceptionnelles pour gaming 4K et montage vid\u00e9o.",
        "prix": 650000, "prix_label": "",
        "categorie": "occasion", "sous_categorie": "occasion-pc",
        "localisation": "Papeete",
        "images": ["pc gamer rtx 4090 64 GIGA DDR5.jpg"],
    },
    {
        "titre": "Studio meubl\u00e9 \u2014 Location Papeete",
        "description": "Studio enti\u00e8rement meubl\u00e9 et \u00e9quip\u00e9 au centre de Papeete. Cuisine am\u00e9ricaine, salle d'eau, climatis\u00e9. Id\u00e9al \u00e9tudiant ou jeune actif.",
        "prix": 60000, "prix_label": "",
        "categorie": "immobilier", "sous_categorie": "immo-appartements",
        "localisation": "Papeete",
        "images": ["studio 1.jpg", "studio 2.jpg", "studio 3.jpg", "studio 4.jpg", "studio 5.jpg"],
    },
]


def _upload_images(annonce, image_files, stdout):
    """Upload les images source vers S3/local via save_webp et retourne les URLs."""
    urls = []
    for img_name in image_files:
        img_path = os.path.join(BASE_IMG, img_name)
        if not os.path.exists(img_path):
            stdout.write(f"    [WARN] Image introuvable : {img_name}")
            continue
        with open(img_path, 'rb') as f:
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            data = f.read()
            fobj = InMemoryUploadedFile(
                io.BytesIO(data), 'photo', img_name, 'image/jpeg', len(data), None
            )
            url = save_webp(fobj, 'annonces', f'{annonce.pk}')
            urls.append(url)
    return urls


class Command(BaseCommand):
    help = 'Importe les 21 vraies annonces TBG avec upload S3'

    def handle(self, *args, **options):
        import os as _os
        bucket = _os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
        self.stdout.write(f"S3 bucket: {'[' + bucket + ']' if bucket else 'NON CONFIGURE (local)'}")

        User = get_user_model()
        user = User.objects.filter(email='admin@tahitibusinessgroup.com').first()
        if not user:
            self.stdout.write(self.style.ERROR('Admin introuvable — lancez create_admin d\'abord.'))
            return

        created = 0
        updated = 0
        for data in ANNONCES:
            annonce = Annonce.objects.filter(titre=data['titre']).first()
            if annonce:
                # Verifier si les photos pointent vers /media/ (local, perdu sur Railway)
                needs_reupload = (
                    not annonce.photos
                    or any(p.startswith('/media/') for p in annonce.photos)
                )
                if needs_reupload and data.get('images'):
                    urls = _upload_images(annonce, data['images'], self.stdout)
                    if urls:
                        annonce.photos = urls
                        annonce.save()
                        updated += 1
                        self.stdout.write(f'  ~ MAJ photos : {data["titre"][:50]} ({len(urls)} photos)')
                    else:
                        self.stdout.write(f'  ~ Existante (pas d\'images source) : {data["titre"][:55]}')
                else:
                    self.stdout.write(f'  ~ OK : {data["titre"][:55]}')
                continue

            annonce = Annonce.objects.create(
                user=user,
                titre=data['titre'],
                description=data['description'],
                prix=data['prix'],
                prix_label=data['prix_label'],
                categorie=data['categorie'],
                sous_categorie=data['sous_categorie'],
                localisation=data['localisation'],
                photos=[],
                statut='actif',
                boost=False,
            )
            if data.get('images'):
                urls = _upload_images(annonce, data['images'], self.stdout)
                annonce.photos = urls
                annonce.save()
                self.stdout.write(f'  + {data["titre"][:50]} ({len(urls)} photos)')
            else:
                self.stdout.write(f'  + {data["titre"][:50]} (sans photos)')
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] {created} creees, {updated} photos mises a jour.'
        ))
