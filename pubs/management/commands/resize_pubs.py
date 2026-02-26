from django.core.management.base import BaseCommand
from django.db.models import Q
from pubs.models import Publicite


class Command(BaseCommand):
    help = "Redimensionne toutes les images de pubs (uploadées ou URL externe) selon leur encart."

    def handle(self, *args, **options):
        pubs = Publicite.objects.filter(
            Q(image_url__gt='') | ~Q(image='')
        )
        total = pubs.count()
        self.stdout.write(f"{total} pub(s) avec image trouvée(s).")

        ok = 0
        skipped = 0
        errors = 0
        for pub in pubs:
            source = 'upload' if pub.image else 'url'
            err = pub._resize_to_slot()
            if err is None:
                ok += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  OK   [{pub.emplacement:16s}][{source}] {pub.titre}")
                )
            elif 'ignoré' in err or 'SVG' in err or 'Aucune' in err:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"  SKIP [{pub.emplacement:16s}][{source}] {pub.titre} — {err}")
                )
            else:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ERR  [{pub.emplacement:16s}][{source}] {pub.titre} — {err}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nTerminé : {ok} OK, {skipped} ignoré(s), {errors} erreur(s).")
        )
