import io
import ipaddress
import os
import uuid
import urllib.request
from urllib.parse import urlparse
from django.conf import settings as django_settings
from django.db import models
from PIL import Image as PILImage, ImageOps as PILImageOps

EMPLACEMENTS = [
    # Billboard
    ("billboard", "Billboard plein écran (100 000 XPF/mois)"),
    # Sidebar droite
    ("sidebar_haut",   "Sidebar Droite — Haut (40 000 XPF/mois)"),
    ("sidebar_milieu", "Sidebar Droite — Milieu (28 000 XPF/mois)"),
    ("sidebar_bas",    "Sidebar Droite — Bas (20 000 XPF/mois)"),
    # Sidebar gauche
    ("sidebar_gauche", "Sidebar Gauche (35 000 XPF/mois)"),
    # Strips Accueil
    ("strip_accueil_haut",   "Strip Accueil — Haut (8 000 XPF/mois)"),
    ("strip_accueil_milieu", "Strip Accueil — Milieu (8 000 XPF/mois)"),
    ("strip_accueil_bas",    "Strip Accueil — Bas (8 000 XPF/mois)"),
    # Strips Immobilier
    ("strip_immo_haut",   "Strip Immobilier — Haut (12 000 XPF/mois)"),
    ("strip_immo_milieu", "Strip Immobilier — Milieu (10 000 XPF/mois)"),
    ("strip_immo_bas",    "Strip Immobilier — Bas (8 000 XPF/mois)"),
    # Strips Véhicules
    ("strip_vehicules_haut",   "Strip Véhicules — Haut (12 000 XPF/mois)"),
    ("strip_vehicules_milieu", "Strip Véhicules — Milieu (10 000 XPF/mois)"),
    ("strip_vehicules_bas",    "Strip Véhicules — Bas (8 000 XPF/mois)"),
    # Strips Occasion
    ("strip_occasion_haut",   "Strip Occasion — Haut (12 000 XPF/mois)"),
    ("strip_occasion_milieu", "Strip Occasion — Milieu (10 000 XPF/mois)"),
    ("strip_occasion_bas",    "Strip Occasion — Bas (8 000 XPF/mois)"),
    # Strips Emploi
    ("strip_emploi_haut",   "Strip Emploi — Haut (12 000 XPF/mois)"),
    ("strip_emploi_milieu", "Strip Emploi — Milieu (10 000 XPF/mois)"),
    ("strip_emploi_bas",    "Strip Emploi — Bas (8 000 XPF/mois)"),
    # Strips Services
    ("strip_services_haut",   "Strip Services — Haut (12 000 XPF/mois)"),
    ("strip_services_milieu", "Strip Services — Milieu (10 000 XPF/mois)"),
    ("strip_services_bas",    "Strip Services — Bas (8 000 XPF/mois)"),
]

PRIX_PAR_EMPLACEMENT = {
    "billboard": 100000,
    "sidebar_haut":   40000,
    "sidebar_milieu": 28000,
    "sidebar_bas":    20000,
    "sidebar_gauche": 35000,
    "strip_accueil_haut":   8000,
    "strip_accueil_milieu": 8000,
    "strip_accueil_bas":    8000,
    "strip_immo_haut":   12000,
    "strip_immo_milieu": 10000,
    "strip_immo_bas":     8000,
    "strip_vehicules_haut":   12000,
    "strip_vehicules_milieu": 10000,
    "strip_vehicules_bas":     8000,
    "strip_occasion_haut":   12000,
    "strip_occasion_milieu": 10000,
    "strip_occasion_bas":     8000,
    "strip_emploi_haut":   12000,
    "strip_emploi_milieu": 10000,
    "strip_emploi_bas":     8000,
    "strip_services_haut":   12000,
    "strip_services_milieu": 10000,
    "strip_services_bas":     8000,
}

DUREE_CHOICES = [
    (1,  '1 semaine'),
    (4,  '1 mois'),
    (12, '3 mois (-10%)'),
    (24, '6 mois (-20%)'),
]

DISCOUNT_PAR_DUREE = {
    1:  0,       # 1 semaine = prix mensuel / 4
    4:  0,       # 1 mois = prix mensuel
    12: 0.10,    # 3 mois = -10%
    24: 0.20,    # 6 mois = -20%
}

PAYMENT_STATUS = [
    ('none',    '—'),
    ('pending', 'En attente'),
    ('paid',    'Payé'),
    ('failed',  'Échoué'),
    ('expired', 'Expiré'),
]


def calculer_prix(emplacement, duree_semaines):
    """Calcule le prix total en XPF pour un emplacement et une durée en semaines."""
    prix_mensuel = PRIX_PAR_EMPLACEMENT.get(emplacement, 0)
    if duree_semaines == 1:
        total = prix_mensuel // 4
    else:
        nb_mois = duree_semaines // 4
        total = prix_mensuel * nb_mois
    discount = DISCOUNT_PAR_DUREE.get(duree_semaines, 0)
    total = int(total * (1 - discount))
    return total

# Dimensions cibles (w × h) par emplacement — crop centré via ImageOps.fit
DIMS_PAR_EMPLACEMENT = {
    "billboard":        (1400, 300),
    "billboard_milieu": (1400, 90),
    "sidebar_haut":     (600, 300),
    "sidebar_milieu":   (600, 270),
    "sidebar_bas":      (600, 240),
    "sidebar_gauche":   (300, 600),
}
# Tous les strips ont les mêmes dimensions
for _s in PRIX_PAR_EMPLACEMENT:
    if _s.startswith('strip_'):
        DIMS_PAR_EMPLACEMENT[_s] = (1200, 150)

# Formats d'image supportés par Pillow (les SVG et autres vecteurs sont exclus)
_SUPPORTED_MIME_PREFIXES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif',
                             'image/bmp', 'image/tiff')


CAT_CHOICES = [
    ('vehicules',  'Véhicules'),
    ('immobilier', 'Immobilier'),
    ('occasion',   'Occasion / Bon Plan'),
    ('emploi',     'Offre et Demande d\'emploi'),
    ('services',   'Service / Prestation'),
]


class Publicite(models.Model):
    titre        = models.CharField(max_length=200)
    description  = models.CharField(max_length=300, blank=True)
    image        = models.ImageField(upload_to='pubs/', blank=True, null=True)
    image_url    = models.URLField(blank=True, help_text="URL externe si pas d'upload")
    video        = models.FileField(upload_to='pubs/videos/', blank=True, null=True)
    video_url    = models.URLField(blank=True, help_text="URL externe d'une vidéo")
    lien         = models.URLField(blank=True)
    emplacement  = models.CharField(max_length=30, choices=EMPLACEMENTS)
    categorie    = models.CharField(max_length=20, choices=CAT_CHOICES, blank=True, default='',
                                    help_text="Catégorie ciblée (uniquement pour emplacements cat_*)")
    prix         = models.IntegerField(default=0)
    actif        = models.BooleanField(default=True)
    client_nom   = models.CharField(max_length=150, blank=True)
    client_email = models.EmailField(blank=True)
    client_tel   = models.CharField(max_length=20, blank=True)
    date_debut   = models.DateField(null=True, blank=True)
    date_fin     = models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    # ── Paiement PayZen ──
    payment_status   = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='none', db_index=True)
    payment_ref      = models.CharField(max_length=64, unique=True, blank=True, null=True,
                                        help_text="Référence unique PayZen (vads_order_id)")
    payment_trans_id = models.CharField(max_length=64, blank=True,
                                        help_text="ID transaction retourné par PayZen")
    duree_semaines   = models.IntegerField(default=4, help_text="Durée achetée en semaines")

    class Meta:
        verbose_name = 'Publicité'
        verbose_name_plural = 'Publicités'
        ordering = ['emplacement', '-actif']

    def __str__(self):
        return f"{self.titre} ({self.get_emplacement_display()})"

    def save(self, *args, **kwargs):
        if not self.prix:
            self.prix = PRIX_PAR_EMPLACEMENT.get(self.emplacement, 0)

        # Détecter si la source image a changé avant de sauvegarder
        image_changed = False
        if self.pk:
            try:
                old = Publicite.objects.get(pk=self.pk)
                uploaded_changed = bool(self.image) and old.image != self.image
                url_changed = (bool(self.image_url) and old.image_url != self.image_url
                               and not self.image)
                image_changed = uploaded_changed or url_changed
            except Publicite.DoesNotExist:
                image_changed = bool(self.image) or bool(self.image_url)
        else:
            image_changed = bool(self.image) or bool(self.image_url)

        super().save(*args, **kwargs)

        if image_changed:
            self._resize_to_slot()

    def _resize_to_slot(self):
        """Redimensionne l'image (uploadée ou URL externe) aux dimensions exactes de l'encart.

        Pour une image uploadée : traitement local.
        Pour une image_url      : téléchargement → vérification format → traitement → WebP local.
        Retourne None si succès, un message d'erreur (str) si échec.
        """
        dims = DIMS_PAR_EMPLACEMENT.get(self.emplacement)
        if not dims:
            return f"Emplacement '{self.emplacement}' sans dimensions définies — ignoré."

        old_path = None
        try:
            # ── Ouvrir l'image selon la source ──────────────────────────────
            if self.image:
                img = PILImage.open(self.image.path)
                old_path = self.image.path
            elif self.image_url:
                parsed = urlparse(self.image_url)
                if parsed.scheme not in ('http', 'https'):
                    return f"Schéma URL non autorisé : {parsed.scheme}"
                host = parsed.hostname or ''
                try:
                    addr = ipaddress.ip_address(host)
                    if addr.is_private or addr.is_loopback or addr.is_link_local:
                        return f"URL privée ou locale non autorisée : {host}"
                except ValueError:
                    if host.lower() in ('localhost', '0.0.0.0') or host.endswith('.local'):
                        return f"Hôte local non autorisé : {host}"
                req = urllib.request.Request(
                    self.image_url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; TBG-bot/1.0)'},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    content_type = resp.headers.get('Content-Type', '').lower()
                    # Rejeter les SVG et formats non-raster (Pillow ne les supporte pas)
                    if 'svg' in content_type or 'xml' in content_type:
                        return f"Format SVG non supporté pour l'URL : {self.image_url}"
                    data = resp.read()
                img = PILImage.open(io.BytesIO(data))
                img.load()
            else:
                return "Aucune source image."

            # ── Traitement ────────────────────────────────────────────────
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img = PILImageOps.fit(img, dims, PILImage.LANCZOS)

            if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
                # ── Upload S3 (production Railway) ────────────────────────
                import boto3
                bucket = os.environ['AWS_STORAGE_BUCKET_NAME']
                region = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')
                key = f"pubs/pub_{self.pk}_{uuid.uuid4().hex[:8]}.webp"
                buf = io.BytesIO()
                img.save(buf, format='WEBP', quality=85, method=6)
                buf.seek(0)
                boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                ).put_object(Bucket=bucket, Key=key, Body=buf, ContentType='image/webp')
                s3_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
                # Supprimer le fichier local temporaire
                if old_path and os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
                Publicite.objects.filter(pk=self.pk).update(image='', image_url=s3_url)
                self.image_url = s3_url
            else:
                # ── Sauvegarde locale en WebP (développement) ─────────────
                upload_dir = os.path.join(django_settings.MEDIA_ROOT, 'pubs')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"pub_{self.pk}_{uuid.uuid4().hex[:8]}.webp"
                new_path = os.path.join(upload_dir, filename)
                img.save(new_path, format='WEBP', quality=85, method=6)
                if old_path and os.path.exists(old_path) and old_path != new_path:
                    os.remove(old_path)
                new_name = f"pubs/{filename}"
                Publicite.objects.filter(pk=self.pk).update(image=new_name, image_url='')
                self.image.name = new_name
                self.image_url = ''
            return None  # succès

        except Exception as e:
            return str(e)  # remonter l'erreur sans bloquer la sauvegarde

    _VIDEO_EXTENSIONS = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.ogv')

    def _is_video_url(self, url):
        """Détecte si une URL pointe vers une vidéo (par extension)."""
        if not url:
            return False
        path = url.split('?')[0].split('#')[0].lower()
        return any(path.endswith(ext) for ext in self._VIDEO_EXTENSIONS)

    def get_image(self):
        if self.image:
            return self.image.url
        if self.image_url and not self._is_video_url(self.image_url):
            return self.image_url
        return None

    def get_video(self):
        if self.video:
            return self.video.url
        if self.video_url:
            return self.video_url
        # Fallback : URL vidéo stockée dans image_url
        if self.image_url and self._is_video_url(self.image_url):
            return self.image_url
        return None

    def is_video(self):
        """Retourne True si le média principal est une vidéo."""
        if self.video or self.video_url:
            return True
        # Détecter une URL vidéo dans image_url
        return self._is_video_url(self.image_url)

    def get_media(self):
        """Retourne (type, url) — type = 'video' ou 'image'."""
        if self.video:
            return ('video', self.video.url)
        if self.video_url:
            return ('video', self.video_url)
        if self.image_url and self._is_video_url(self.image_url):
            return ('video', self.image_url)
        if self.image:
            return ('image', self.image.url)
        if self.image_url:
            return ('image', self.image_url)
        return (None, None)


class DemandePublicite(models.Model):
    nom                  = models.CharField(max_length=150)
    email                = models.EmailField()
    tel                  = models.CharField(max_length=20, blank=True)
    entreprise           = models.CharField(max_length=200, blank=True)
    emplacement_souhaite = models.CharField(max_length=30, choices=EMPLACEMENTS)
    message              = models.TextField(blank=True)
    traite               = models.BooleanField(default=False)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Demande de pub'
        verbose_name_plural = 'Demandes de pub'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom} — {self.emplacement_souhaite}"
