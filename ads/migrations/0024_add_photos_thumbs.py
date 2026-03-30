# Generated manually on 2026-03-30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0023_populate_annonce_slugs'),
    ]

    operations = [
        migrations.AddField(
            model_name='annonce',
            name='photos_thumbs',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
