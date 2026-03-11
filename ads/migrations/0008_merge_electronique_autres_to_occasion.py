"""Fusionne les catégories 'electronique' et 'autres' en 'occasion'."""

from django.db import migrations


def forwards(apps, schema_editor):
    Annonce = apps.get_model('ads', 'Annonce')

    # Mapping sous-catégories : ancien code → nouveau code
    sous_cat_map = {
        # electronique → occasion
        'elec-telephones':     'occasion-telephones',
        'elec-ordinateurs':    'occasion-ordinateurs',
        'elec-pc':             'occasion-pc',
        'elec-tv':             'occasion-tv',
        'elec-jeux':           'occasion-jeux-video',
        'elec-electromenager': 'occasion-electromenager',
        # autres → occasion
        'autres-meubles':      'occasion-meubles',
        'autres-vetements':    'occasion-vetements',
        'autres-sport':        'occasion-sport',
        'autres-puericulture': 'occasion-puericulture',
        'autres-jeux':         'occasion-jeux-jouets',
        'autres-divers':       'occasion-divers',
    }

    # Migrer les annonces electronique → occasion
    Annonce.objects.filter(categorie='electronique').update(categorie='occasion')
    # Migrer les annonces autres → occasion
    Annonce.objects.filter(categorie='autres').update(categorie='occasion')

    # Migrer les sous-catégories
    for old_code, new_code in sous_cat_map.items():
        Annonce.objects.filter(sous_categorie=old_code).update(sous_categorie=new_code)


def backwards(apps, schema_editor):
    Annonce = apps.get_model('ads', 'Annonce')

    # Sous-catégories occasion-elec* → electronique
    elec_sous_cats = [
        'occasion-telephones', 'occasion-ordinateurs', 'occasion-pc',
        'occasion-tv', 'occasion-jeux-video', 'occasion-electromenager',
    ]
    Annonce.objects.filter(
        categorie='occasion', sous_categorie__in=elec_sous_cats
    ).update(categorie='electronique')

    # Le reste → autres
    Annonce.objects.filter(categorie='occasion').update(categorie='autres')

    # Remap sous-catégories
    reverse_map = {
        'occasion-telephones':     'elec-telephones',
        'occasion-ordinateurs':    'elec-ordinateurs',
        'occasion-pc':             'elec-pc',
        'occasion-tv':             'elec-tv',
        'occasion-jeux-video':     'elec-jeux',
        'occasion-electromenager': 'elec-electromenager',
        'occasion-meubles':        'autres-meubles',
        'occasion-vetements':      'autres-vetements',
        'occasion-sport':          'autres-sport',
        'occasion-puericulture':   'autres-puericulture',
        'occasion-jeux-jouets':    'autres-jeux',
        'occasion-divers':         'autres-divers',
    }
    for old_code, new_code in reverse_map.items():
        Annonce.objects.filter(sous_categorie=old_code).update(sous_categorie=new_code)


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0007_boost_status_expires'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
