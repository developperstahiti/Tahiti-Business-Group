from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0005_signalement'),
    ]

    operations = [
        migrations.AddField(
            model_name='annonce',
            name='boost_duree',
            field=models.CharField(
                blank=True, default='',
                choices=[
                    ('', 'Sans boost'),
                    ('1jour', '1 jour gratuit'),
                    ('7jours', '7 jours (payant)'),
                    ('1mois', '1 mois (payant)'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='annonce',
            name='boost_demande',
            field=models.TextField(blank=True, default=''),
        ),
    ]
