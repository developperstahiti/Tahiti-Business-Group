"""Génère des codes de parrainage uniques + étoiles fake pour tous les users.

Idempotent : ne touche pas les users qui ont déjà leur referral_code rempli
(et fake_rating > 0). Peut être lancé plusieurs fois sans problème.

Usage :
    python manage.py populate_user_engagement
    python manage.py populate_user_engagement --force   # régénère tout
"""
import random
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


def _generate_unique_code(used_codes, length=8):
    chars = string.ascii_uppercase + string.digits
    for _ in range(50):
        code = ''.join(random.choices(chars, k=length))
        if code not in used_codes:
            return code
    return None


class Command(BaseCommand):
    help = "Peuple referral_code, fake_rating et fake_review_count sur tous les users"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Régénère même si déjà peuplé.')
        parser.add_argument('--batch', type=int, default=200,
                            help='Taille des batches de save (défaut 200).')

    def handle(self, *args, **opts):
        force = opts['force']
        batch_size = opts['batch']

        used_codes = set(User.objects.exclude(referral_code='')
                                     .values_list('referral_code', flat=True))

        total = 0
        updated = 0
        skipped = 0
        batch = []

        qs = User.objects.all().iterator(chunk_size=batch_size)

        for user in qs:
            total += 1
            changed = False

            if force or not user.referral_code:
                code = _generate_unique_code(used_codes)
                if code:
                    user.referral_code = code
                    used_codes.add(code)
                    changed = True

            if force or not user.fake_rating:
                user.fake_rating = round(random.triangular(3.9, 5.0, 4.5), 2)
                user.fake_review_count = random.randint(5, 80)
                changed = True

            if changed:
                user.save(update_fields=['referral_code', 'fake_rating', 'fake_review_count'])
                updated += 1
            else:
                skipped += 1

            if total % 100 == 0:
                self.stdout.write(f'  ...{total} users traités ({updated} mis à jour, {skipped} skip)')

        self.stdout.write(self.style.SUCCESS(
            f'OK : {total} users parcourus, {updated} mis à jour, {skipped} skip.'
        ))
