"""Utilitaire WebP partagé — annonces et rubriques."""
import io
import os
import uuid
from django.conf import settings as django_settings
from PIL import Image as PILImage


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
    img = PILImage.open(file_obj)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail(max_size, PILImage.LANCZOS)

    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.webp"

    if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
        import boto3
        bucket = os.environ['AWS_STORAGE_BUCKET_NAME']
        region = os.environ.get('AWS_S3_REGION_NAME', 'eu-north-1')
        key = f"{folder}/{filename}"
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=85, method=6)
        buf.seek(0)
        boto3.client(
            's3', region_name=region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        ).put_object(Bucket=bucket, Key=key, Body=buf, ContentType='image/webp')
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

    upload_dir = os.path.join(django_settings.MEDIA_ROOT, folder)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    img.save(filepath, format='WEBP', quality=85, method=6)
    return f"{django_settings.MEDIA_URL}{folder}/{filename}"
