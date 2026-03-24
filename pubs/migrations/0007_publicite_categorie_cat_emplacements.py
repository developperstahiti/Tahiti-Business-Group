from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pubs', '0006_add_video_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicite',
            name='categorie',
            field=models.CharField(
                blank=True, default='', max_length=20,
                choices=[
                    ('vehicules', 'Véhicules'),
                    ('immobilier', 'Immobilier'),
                    ('occasion', 'Occasion'),
                    ('emploi', 'Emploi'),
                    ('services', 'Services'),
                ],
                help_text='Catégorie ciblée (uniquement pour emplacements cat_*)',
            ),
        ),
        migrations.AlterField(
            model_name='publicite',
            name='emplacement',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('billboard', 'Billboard plein écran (100 000 XPF/mois)'),
                    ('strip_1', 'Strip 1 - Après Promos (8 000 XPF/mois)'),
                    ('strip_2', 'Strip 2 - Milieu page (8 000 XPF/mois)'),
                    ('strip_3', 'Strip 3 - Fin de page (8 000 XPF/mois)'),
                    ('haut', 'Sidebar Haut (40 000 XPF/mois)'),
                    ('milieu', 'Sidebar Milieu (28 000 XPF/mois)'),
                    ('bas', 'Sidebar Bas (20 000 XPF/mois)'),
                    ('cat_haut', 'Catégorie — Haut (15 000 XPF/mois)'),
                    ('cat_milieu', 'Catégorie — Milieu (12 000 XPF/mois)'),
                    ('cat_bas', 'Catégorie — Bas (10 000 XPF/mois)'),
                ],
            ),
        ),
    ]
