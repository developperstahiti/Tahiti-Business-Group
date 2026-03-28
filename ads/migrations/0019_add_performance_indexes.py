from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0018_fix_old_annonces_defaults"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="annonce",
            index=models.Index(fields=["statut"], name="idx_annonce_statut"),
        ),
        migrations.AddIndex(
            model_name="annonce",
            index=models.Index(fields=["categorie"], name="idx_annonce_categorie"),
        ),
        migrations.AddIndex(
            model_name="annonce",
            index=models.Index(fields=["statut", "categorie"], name="idx_annonce_stat_cat"),
        ),
        migrations.AddIndex(
            model_name="annonce",
            index=models.Index(fields=["-created_at"], name="idx_annonce_created"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["to_user", "read", "created_at"], name="idx_msg_unread"),
        ),
    ]
