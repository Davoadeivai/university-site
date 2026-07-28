from django.core.management.base import BaseCommand

from admissions.tuition_seed import ensure_tuition_structures_for_active_majors


class Command(BaseCommand):
    help = 'ایجاد ساختار شهریه برای رشته‌های فعال فاقد شهریه (همه مقاطع)'

    def handle(self, *args, **options):
        result = ensure_tuition_structures_for_active_majors()
        self.stdout.write(
            self.style.SUCCESS(
                f"year={result['academic_year']} created={result['created']} "
                f"reactivated={result['reactivated']} skipped={result['skipped']}"
            )
        )
