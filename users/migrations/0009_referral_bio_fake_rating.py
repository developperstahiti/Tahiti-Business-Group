"""Add referral system + enriched profile + fake rating fields on User.

Idempotent migration : utilise RunSQL avec ADD COLUMN IF NOT EXISTS pour éviter
les échecs si la migration est ré-appliquée ou si une partie a déjà été appliquée
manuellement. Les valeurs par défaut sont OK pour démarrer (fake_rating=0,
referral_code='') — un management command séparé `populate_user_engagement`
génère ensuite des valeurs réalistes.

Le unique=True sur referral_code est ajouté plus tard, après que la commande
de population ait peuplé tous les codes.
"""
from django.db import migrations, models


_ADD_COLUMNS_SQL = [
    # referral_code (sans unique pour l'instant, ajouté après populate)
    "ALTER TABLE users_user ADD COLUMN IF NOT EXISTS referral_code varchar(20) DEFAULT '' NOT NULL",
    # referred_by FK self
    "ALTER TABLE users_user ADD COLUMN IF NOT EXISTS referred_by_id bigint NULL "
    "REFERENCES users_user(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED",
    # referral_rewards_earned
    "ALTER TABLE users_user ADD COLUMN IF NOT EXISTS referral_rewards_earned integer DEFAULT 0 NOT NULL "
    "CHECK (referral_rewards_earned >= 0)",
    # bio
    "ALTER TABLE users_user ADD COLUMN IF NOT EXISTS bio text DEFAULT '' NOT NULL",
    # fake_rating
    "ALTER TABLE users_user ADD COLUMN IF NOT EXISTS fake_rating double precision DEFAULT 0 NOT NULL",
    # fake_review_count
    "ALTER TABLE users_user ADD COLUMN IF NOT EXISTS fake_review_count integer DEFAULT 0 NOT NULL "
    "CHECK (fake_review_count >= 0)",
    # Index sur referral_code
    "CREATE INDEX IF NOT EXISTS users_user_referral_code_idx ON users_user(referral_code)",
    # Index sur referred_by_id
    "CREATE INDEX IF NOT EXISTS users_user_referred_by_id_idx ON users_user(referred_by_id)",
]

_DROP_COLUMNS_SQL = [
    "DROP INDEX IF EXISTS users_user_referred_by_id_idx",
    "DROP INDEX IF EXISTS users_user_referral_code_idx",
    "ALTER TABLE users_user DROP COLUMN IF EXISTS fake_review_count",
    "ALTER TABLE users_user DROP COLUMN IF EXISTS fake_rating",
    "ALTER TABLE users_user DROP COLUMN IF EXISTS bio",
    "ALTER TABLE users_user DROP COLUMN IF EXISTS referral_rewards_earned",
    "ALTER TABLE users_user DROP COLUMN IF EXISTS referred_by_id",
    "ALTER TABLE users_user DROP COLUMN IF EXISTS referral_code",
]


_STATE_OPERATIONS = [
    migrations.AddField(
        model_name='user',
        name='referral_code',
        field=models.CharField(
            blank=True, db_index=True, default='',
            help_text='Code unique de parrainage (auto-généré)',
            max_length=20,
        ),
    ),
    migrations.AddField(
        model_name='user',
        name='referred_by',
        field=models.ForeignKey(
            blank=True, null=True,
            help_text='Qui a parrainé ce user',
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
            blank=True, default='',
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
            help_text="Nombre d'avis fictifs (cohérent avec fake_rating)",
        ),
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_is_imported'),
    ]

    operations = [
        migrations.RunSQL(
            sql='; '.join(_ADD_COLUMNS_SQL) + ';',
            reverse_sql='; '.join(_DROP_COLUMNS_SQL) + ';',
            state_operations=_STATE_OPERATIONS,
        ),
    ]
