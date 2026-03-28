from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pubs", "0010_alter_publicite_categorie"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="publicite",
            index=models.Index(fields=["emplacement", "actif"], name="idx_pub_empl_actif"),
        ),
    ]
