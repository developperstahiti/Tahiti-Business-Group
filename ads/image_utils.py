"""Utilitaire WebP partagé — annonces et rubriques."""
import io
import logging
import os
import uuid
from django.conf import settings as django_settings
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


def save_webp(file_obj, folder, prefix, max_size=(1200, 900)):
    """Convertit un upload image en WebP, sauvegarde localement ou sur S3.

    Args:
        file_obj  : fichier uploadé (InMemoryUploadedFile ou similaire)
        folder    : sous-dossier dans media/ et dans le bucket S3 (ex: 'annonces')
        prefix    : préfixe du nom de fichier (ex: '42' ou 'promo_5')
        max_size  : tuple (width, height) max pour thumbnail

    Returns:
        URL publique (str)
    """
    if hasattr(file_obj, 'size') and file_obj.size > _MAX_FILE_SIZE:
        raise ValueError("Fichier trop volumineux (max 5 Mo).")

    _check_magic_bytes(file_obj)

    img = PILImage.open(file_obj)
    if img.format not in _ALLOWED_FORMATS:
        raise ValueError(f"Format d'image non autorisé : {img.format}.")
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail(max_size, PILImage.LANCZOS)

    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.webp"

    if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
        import boto3
        from botocore.exceptions import ClientError
        bucket = os.environ['AWS_STORAGE_BUCKET_NAME']
        region = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')
        key = f"{folder}/{filename}"
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=85, method=6)
        buf.seek(0)
        logger.info("Upload S3: bucket=%s key=%s region=%s", bucket, key, region)
        s3 = boto3.client(
            's3', region_name=region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        )
        # Essayer avec ACL d'abord, puis sans (buckets récents désactivent les ACL)
        try:
            s3.put_object(
                Bucket=bucket, Key=key, Body=buf,
                ContentType='image/webp',
                ACL='public-read',
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.warning("S3 ACL refusé (%s), retry sans ACL: %s", error_code, e)
            buf.seek(0)
            s3.put_object(
                Bucket=bucket, Key=key, Body=buf,
                ContentType='image/webp',
            )
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        logger.info("Upload S3 OK: %s", url)
        return url

    upload_dir = os.path.join(django_settings.MEDIA_ROOT, folder)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    img.save(filepath, format='WEBP', quality=85, method=6)
    return f"{django_settings.MEDIA_URL}{folder}/{filename}"
