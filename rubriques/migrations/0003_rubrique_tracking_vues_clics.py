# Generated manually on 2026-04-04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rubriques', '0002_articleinfo_photo_articlenouveaute_photo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='articlepromo',
            name='nb_vues',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='articlepromo',
            name='nb_clics',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='articleinfo',
            name='nb_vues',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='articleinfo',
            name='nb_clics',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='articlenouveaute',
            name='nb_vues',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='articlenouveaute',
            name='nb_clics',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
