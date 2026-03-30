"""Utilitaire WebP partagé — annonces et rubriques."""
import io
import logging
import os
import uuid
from django.conf import settings as django_settings
from django.core.files.base import ContentFile
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo
_ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}

_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'RIFF': 'image/webp',  # WebP commence par RIFF....WEBP
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
}

# Constantes de compression
MAX_WIDTH = 1200
MAX_HEIGHT = 900
QUALITY = 82

THUMB_WIDTH = 400
THUMB_HEIGHT = 300


def _check_magic_bytes(file_obj):
    """Verifie les magic bytes du fichier pour s'assurer que c'est une vraie image."""
    pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
    header = file_obj.read(12)
    file_obj.seek(pos)

    if not header:
        raise ValueError("Fichier vide.")

    for magic, mime in _MAGIC_BYTES.items():
        if header.startswith(magic):
            # Pour WebP, verifier aussi que "WEBP" est a l'offset 8
            if magic == b'RIFF' and header[8:12] != b'WEBP':
                continue
            return mime

    raise ValueError("Format de fichier non autorise (magic bytes invalides).")


def compress_image(image_file, max_width=MAX_WIDTH, max_height=MAX_HEIGHT, quality=QUALITY):
    """
    Compresse et redimensionne une image uploadée en WebP.
    Retourne un ContentFile WebP.
    """
    img = PILImage.open(image_file)

    # Convertir en RGB si nécessaire (PNG avec transparence, palette)
    if img.mode in ('RGBA', 'P', 'LA'):
        background = PILImage.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Redimensionner si trop grande (conserve le ratio)
    img.thumbnail((max_width, max_height), PILImage.LANCZOS)

    # Sauvegarder en WebP
    output = io.BytesIO()
    img.save(output, format='WEBP', quality=quality, optimize=True, method=6)
    output.seek(0)

    # Renommer en .webp
    original_name = getattr(image_file, 'name', 'image.jpg')
    filename = original_name.rsplit('.', 1)[0] + '.webp'

    return ContentFile(output.read(), name=filename)


def make_thumbnail(image_file):
    """
    Crée une miniature 400x300 (crop centré) en WebP.
    Retourne un ContentFile WebP.
    """
    img = PILImage.open(image_file)

    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Crop centré pour remplir exactement 400x300
    target_ratio = THUMB_WIDTH / THUMB_HEIGHT
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        # Image trop large : recadrer les côtés
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image trop haute : recadrer haut/bas
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))

    img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), PILImage.LANCZOS)

    output = io.BytesIO()
    img.save(output, format='WEBP', quality=80, optimize=True)
    output.seek(0)

    original_name = getattr(image_file, 'name', 'image.jpg')
    base = original_name.rsplit('.', 1)[0]
    filename = base + '_thumb.webp'

    return ContentFile(output.read(), name=filename)


def save_webp(file_obj, folder, prefix, max_size=(MAX_WIDTH, MAX_HEIGHT), with_thumb=False):
    """Convertit un upload image en WebP, sauvegarde localement ou sur S3.

    Args:
        file_obj   : fichier uploadé (InMemoryUploadedFile ou similaire)
        folder     : sous-dossier dans media/ et dans le bucket S3 (ex: 'annonces')
        prefix     : préfixe du nom de fichier (ex: '42' ou 'promo_5')
        max_size   : tuple (width, height) max pour redimensionnement
        with_thumb : si True, génère aussi un thumbnail 400x300 et retourne (url, thumb_url)

    Returns:
        URL publique (str) si with_thumb=False
        (url, thumb_url) (tuple) si with_thumb=True
    """
    if hasattr(file_obj, 'size') and file_obj.size > _MAX_FILE_SIZE:
        raise ValueError("Fichier trop volumineux (max 5 Mo).")

    _check_magic_bytes(file_obj)

    img = PILImage.open(file_obj)
    if img.format not in _ALLOWED_FORMATS:
        raise ValueError(f"Format d'image non autorisé : {img.format}.")

    # Convertir en RGB si nécessaire
    if img.mode in ('RGBA', 'P', 'LA'):
        background = PILImage.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail(max_size, PILImage.LANCZOS)

    uid = uuid.uuid4().hex[:8]
    filename = f"{prefix}_{uid}.webp"
    thumb_filename = f"{prefix}_{uid}_thumb.webp"

    # Préparer le buffer image principale
    buf = io.BytesIO()
    img.save(buf, format='WEBP', quality=QUALITY, method=6)
    buf.seek(0)

    # Préparer le buffer thumbnail si demandé
    thumb_buf = None
    if with_thumb:
        thumb_img = img.copy()
        target_ratio = THUMB_WIDTH / THUMB_HEIGHT
        img_ratio = thumb_img.width / thumb_img.height
        if img_ratio > target_ratio:
            new_width = int(thumb_img.height * target_ratio)
            left = (thumb_img.width - new_width) // 2
            thumb_img = thumb_img.crop((left, 0, left + new_width, thumb_img.height))
        else:
            new_height = int(thumb_img.width / target_ratio)
            top = (thumb_img.height - new_height) // 2
            thumb_img = thumb_img.crop((0, top, thumb_img.width, top + new_height))
        thumb_img = thumb_img.resize((THUMB_WIDTH, THUMB_HEIGHT), PILImage.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb_img.save(thumb_buf, format='WEBP', quality=80, optimize=True)
        thumb_buf.seek(0)

    if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
        import boto3
        from botocore.exceptions import ClientError
        bucket = os.environ['AWS_STORAGE_BUCKET_NAME']
        region = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')
        key = f"{folder}/{filename}"
        logger.info("Upload S3: bucket=%s key=%s region=%s", bucket, key, region)
        s3 = boto3.client(
            's3', region_name=region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        )

        def _put(k, b):
            # Essayer avec ACL d'abord, puis sans (buckets récents désactivent les ACL)
            try:
                s3.put_object(
                    Bucket=bucket, Key=k, Body=b,
                    ContentType='image/webp',
                    ACL='public-read',
                )
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                logger.warning("S3 ACL refusé (%s), retry sans ACL: %s", error_code, e)
                b.seek(0)
                s3.put_object(
                    Bucket=bucket, Key=k, Body=b,
                    ContentType='image/webp',
                )

        _put(key, buf)
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        logger.info("Upload S3 OK: %s", url)

        if with_thumb and thumb_buf is not None:
            thumb_key = f"{folder}/{thumb_filename}"
            try:
                _put(thumb_key, thumb_buf)
                thumb_url = f"https://{bucket}.s3.{region}.amazonaws.com/{thumb_key}"
                logger.info("Upload S3 thumb OK: %s", thumb_url)
            except Exception as e:
                logger.error("Erreur upload thumbnail S3: %s", e)
                thumb_url = url  # fallback : URL principale
            return url, thumb_url

        return url

    # Stockage local (dev)
    upload_dir = os.path.join(django_settings.MEDIA_ROOT, folder)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(buf.getvalue())
    url = f"{django_settings.MEDIA_URL}{folder}/{filename}"

    if with_thumb and thumb_buf is not None:
        try:
            thumb_filepath = os.path.join(upload_dir, thumb_filename)
            with open(thumb_filepath, 'wb') as f:
                f.write(thumb_buf.getvalue())
            thumb_url = f"{django_settings.MEDIA_URL}{folder}/{thumb_filename}"
        except Exception as e:
            logger.error("Erreur sauvegarde thumbnail local: %s", e)
            thumb_url = url  # fallback
        return url, thumb_url

    return url
