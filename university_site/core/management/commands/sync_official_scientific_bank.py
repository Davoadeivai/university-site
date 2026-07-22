"""
هم‌سان‌سازی بانک اطلاعات علمی با سایت رسمی aab.ac.ir
Run: python manage.py sync_official_scientific_bank
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from research.models import Journal

JOURNAL_SECTIONS = [
    {
        'title': 'نشریه های علمی - پژوهشی',
        'slug': 'nashriye-elmi-pazhouheshi',
        'category': 'scientific',
        'description': 'فهرست نشریه‌های علمی - پژوهشی (مطابق سایت رسمی موسسه).',
        'order': 1,
    },
    {
        'title': 'نشریات دارای اشتراک on-line',
        'slug': 'nashriyat-online-subscription',
        'category': 'online_sub',
        'description': 'نشریات دارای اشتراک آنلاین (مطابق سایت رسمی موسسه).',
        'order': 2,
    },
]


class Command(BaseCommand):
    help = 'Sync scientific bank (journals categories) with official aab.ac.ir'

    def handle(self, *args, **options):
        for spec in JOURNAL_SECTIONS:
            slug = spec['slug'] or slugify(spec['title'], allow_unicode=True)
            obj, created = Journal.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': spec['title'],
                    'category': spec['category'],
                    'description': spec['description'],
                    'order': spec['order'],
                    'is_active': True,
                },
            )
            self.stdout.write(
                f"  journal {'created' if created else 'updated'}: {obj.title}"
            )
        self.stdout.write(self.style.SUCCESS('Scientific bank journals synced'))
