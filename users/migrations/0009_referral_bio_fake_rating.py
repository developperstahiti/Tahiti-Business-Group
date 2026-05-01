"""Add referral system + enriched profile + fake rating fields on User.

Single migration that:
1. Adds all new fields (referral_code without unique=True initially).
2. Runs a data migration to populate referral_code, fake_rating, fake_review_count
   on every existing user.
3. Alters referral_code to add unique=True.
"""

import random
import string

from django.db import migrations, models


def populate_fake_ratings(apps, schema_editor):
    User = apps.get_model('users', 'User')
    used_codes = set(
        User.objects.exclude(referral_code='').values_list('referral_code', flat=True)
    )
    chars = string.ascii_uppercase + string.digits

    for user in User.objects.all():
        # Note d'affichage entre 3.9 et 5.0 (triangulaire centre 4.5 pour realisme)
        user.fake_rating = round(random.triangular(3.9, 5.0, 4.5), 2)
        # Nombre d'avis entre 5 et 80
        user.fake_review_count = random.randint(5, 80)

        if not user.referral_code:
            for _ in range(50):
                code = ''.join(random.choices(chars, k=8))
                if code not in used_codes:
                    used_codes.add(code)
                    user.referral_code = code
                    break

        user.save(update_fields=['fake_rating', 'fake_review_count', 'referral_code'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_is_imported'),
    ]

    operations = [
        # 1. Add fields (referral_code without unique pour eviter conflits avec default '')
        migrations.AddField(
            model_name='user',
            name='referral_code',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Code unique de parrainage (auto-généré)',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='referred_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Qui a parrainé ce user',
                null=True,
                on_delete=models.SET_NULL,
                related_name='referrals',
                to='users.user',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='referral_rewards_earned',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Nb de récompenses (boosts gratuits) gagnées',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Présentation libre du vendeur',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='fake_rating',
            field=models.FloatField(
                default=0,
                help_text="Note d'affichage 3.9-5.0 utilisée si pas de vraies notes",
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='fake_review_count',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Nombre d\'avis fictifs (cohérent avec fake_rating)',
            ),
        ),

        # 2. Populate fake ratings + referral codes on existing users
        migrations.RunPython(populate_fake_ratings, reverse_code=reverse_noop),

        # 3. Now ajouter le unique=True sur referral_code (tous les codes sont uniques)
        migrations.AlterField(
            model_name='user',
            name='referral_code',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Code unique de parrainage (auto-généré)',
                max_length=20,
                unique=True,
            ),
        ),
    ]
