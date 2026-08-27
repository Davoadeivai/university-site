"""ترتیب گروه‌های آموزشی در منو و صفحه‌ها.

    python manage.py set_group_order --list
    python manage.py set_group_order

موسسه خواست سه گروه اول این‌ها باشند:

    ۱. گروه مدیریت صنعتی و مالی
    ۲. گروه مدیریت بازرگانی
    ۳. گروه علوم تربیتی - مدیریت آموزشی

بقیه پس از آن‌ها می‌آیند، به همان ترتیبی که تا امروز داشتند — تا
جابه‌جایی بی‌دلیل نشود.

گروهی که در فهرست بالا نیست و بعداً ساخته می‌شود، ته صف می‌رود؛
دستور بارها قابل اجراست و هر بار همین چیدمان را می‌سازد.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from academics.models import AcademicGroup

FIRST = [
    'مدیریت صنعتی و مالی',
    'مدیریت بازرگانی',
    'علوم تربیتی',
]


def key(text: str) -> str:
    """کلید مقایسه — فاصله، نیم‌فاصله و «گروه» را نادیده می‌گیرد."""
    cleaned = (text or '').replace('ي', 'ی').replace('ك', 'ک')
    cleaned = cleaned.replace('‌', ' ').replace('‏', '')
    for dash in ('-', '–', '—'):
        cleaned = cleaned.replace(dash, ' ')
    cleaned = cleaned.replace('گروه', '')
    return ''.join(cleaned.split())


class Command(BaseCommand):
    help = 'چیدن ترتیب گروه‌های آموزشی'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')
        parser.add_argument('--list', action='store_true',
                            help='ترتیب فعلی را نشان بده')

    def handle(self, *args, **options):
        groups = list(AcademicGroup.objects.all().order_by('order', 'name'))
        if not groups:
            self.stdout.write(self.style.WARNING('گروهی ثبت نشده.'))
            return

        if options['list']:
            for group in groups:
                self.stdout.write('  %2d  %s' % (group.order, group.name))
            return

        wanted = []
        for needle in FIRST:
            match = next((g for g in groups
                          if key(needle) in key(g.name) and g not in wanted),
                         None)
            if match is None:
                self.stdout.write(self.style.WARNING(
                    '  ? «%s» پیدا نشد' % needle))
                continue
            wanted.append(match)

        # بقیه به همان ترتیب فعلی، پس از سه‌تای اول
        wanted += [g for g in groups if g not in wanted]

        changed = 0
        for position, group in enumerate(wanted, start=1):
            if group.order == position:
                continue
            group.order = position
            if not options['dry_run']:
                group.save(update_fields=['order'])
            changed += 1

        head = 'اگر اجرا شود:' if options['dry_run'] else 'انجام شد:'
        self.stdout.write(self.style.SUCCESS(head))
        for position, group in enumerate(wanted, start=1):
            self.stdout.write('  %2d  %s' % (position, group.name))
        self.stdout.write('')
        self.stdout.write('  %d گروه جابه‌جا شد' % changed)
        if options['dry_run']:
            self.stdout.write('(‎--dry-run‎ بود؛ دیتابیس دست‌نخورده ماند.)')
