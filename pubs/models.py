import io
import os
import uuid
import urllib.request
from django.conf import settings as django_settings
from django.db import models
from PIL import Image as PILImage, ImageOps as PILImageOps

EMPLACEMENTS = [
    ("billboard", "Billboard plein ecran (25 000 XPF/mois)"),
    ("strip_1",   "Strip 1 - Apres Promos (8 000 XPF/mois)"),
    ("strip_2",   "Strip 2 - Milieu page (8 000 XPF/mois)"),
    ("strip_3",   "Strip 3 - Fin de page (8 000 XPF/mois)"),
    ("haut",      "Sidebar Haut (10 000 XPF/mois)"),
    ("milieu",    "Sidebar Milieu (7 000 XPF/mois)"),
    ("bas",       "Sidebar Bas (5 000 XPF/mois)"),
]

PRIX_PAR_EMPLACEMENT = {
    "billboard": 25000,
    "strip_1":    8000,
    "strip_2":    8000,
    "strip_3":    8000,
    "haut":      10000,
    "milieu":     7000,
    "bas":        5000,
}

# Dimensions cibles (w × h) par emplacement — crop centré via ImageOps.fit
DIMS_PAR_EMPLACEMENT = {
    "billboard":        (1400, 300),
    "billboard_milieu": (1400, 90),
    "strip_1":          (1400, 90),
    "strip_2":          (1400, 90),
    "strip_3":          (1400, 90),
    "haut":             (600, 300),
    "milieu":           (600, 270),
    "bas":              (600, 240),
}

# Formats d'image supportés par Pillow (les SVG et autres vecteurs sont exclus)
_SUPPORTED_MIME_PREFIXES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif',
                             'image/bmp', 'image/tiff')


class Publicite(models.Model):
    titre        = models.CharField(max_length=200)
    description  = models.CharField(max_length=300, blank=True)
    image        = models.ImageField(upload_to='pubs/', blank=True, null=True)
    image_url    = models.URLField(blank=True, help_text="URL externe si pas d'upload")
    lien         = models.URLField(blank=True)
    emplacement  = models.CharField(max_length=20, choices=EMPLACEMENTS)
    prix         = models.IntegerField(default=0)
    actif        = models.BooleanField(default=True)
    client_nom   = models.CharField(max_length=150, blank=True)
    client_email = models.EmailField(blank=True)
    client_tel   = models.CharField(max_length=20, blank=True)
    date_debut   = models.DateField(null=True, blank=True)
    date_fin     = models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

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

    def get_image(self):
        if self.image:
            return self.image.url
        return self.image_url or None


class DemandePublicite(models.Model):
    nom                  = models.CharField(max_length=150)
    email                = models.EmailField()
    tel                  = models.CharField(max_length=20, blank=True)
    entreprise           = models.CharField(max_length=200, blank=True)
    emplacement_souhaite = models.CharField(max_length=20, choices=EMPLACEMENTS)
    message              = models.TextField(blank=True)
    traite               = models.BooleanField(default=False)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Demande de pub'
        verbose_name_plural = 'Demandes de pub'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom} — {self.emplacement_souhaite}"
