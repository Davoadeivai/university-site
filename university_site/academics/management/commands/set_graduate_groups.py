"""گروه‌های دارای تحصیلات تکمیلی را علامت می‌زند.

    python manage.py set_graduate_groups
    python manage.py set_graduate_groups --list

بند ۱۷ سند اصلاحات موسسه، چهار گروه را نام می‌برد:
بازرگانی، صنعتی، علوم تربیتی، حسابداری — و می‌خواهد همین ترتیب زیر
منوی تحصیلات تکمیلی بیاید.

تشخیص گروه از روی نام انجام می‌شود، نه شناسه: نام گروه‌ها در پنل
دست ادمین است و ممکن است «گروه آموزشی حسابداری» یا فقط «حسابداری»
نوشته شده باشد. مقایسه با نادیده‌گرفتن فاصله و شکل حروف است.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from academics.models import AcademicGroup

# ترتیب همان است که سند خواسته
WANTED = [
    ('بازرگانی', 1),
    ('صنعتی', 2),
    ('علومتربیتی', 3),
    ('حسابداری', 4),
]


def key(name: str) -> str:
    """کلید مقایسه — فاصله، نیم‌فاصله و شکل حروف را نادیده می‌گیرد."""
    cleaned = (name or '')
    cleaned = cleaned.replace('ي', 'ی').replace('ك', 'ک')
    cleaned = cleaned.replace('‌', '').replace('‏', '')
    for word in ('گروه', 'آموزشی', 'آموزش'):
        cleaned = cleaned.replace(word, '')
    return ''.join(cleaned.split())


class Command(BaseCommand):
    help = 'علامت‌زدن گروه‌های دارای تحصیلات تکمیلی (بند ۱۷ سند اصلاحات)'

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true',
                            help='فقط نام گروه‌های موجود را نشان بده')

    def handle(self, *args, **options):
        groups = list(AcademicGroup.objects.all())

        if options['list']:
            self.stdout.write('گروه‌های ثبت‌شده:')
            for group in groups:
                self.stdout.write('  %s  (کلید: %s)' % (group.name, key(group.name)))
            return

        if not groups:
            self.stdout.write(self.style.WARNING(
                'هیچ گروهی ثبت نشده — چیزی برای علامت‌زدن نیست.'))
            return

        found, missing = [], []
        taken = set()

        def match(wanted):
            """گروهی که نامش شامل کلیدواژهٔ سند است.

            تطبیق دقیق کار نمی‌کند: سند «بازرگانی» نوشته و نام واقعی
            «گروه مدیریت بازرگانی» است، «صنعتی» در برابر «گروه مدیریت
            صنعتی و مالی»، و «علوم تربیتی» در برابر «گروه علوم تربیتی -
            مدیریت آموزشی». پس زیررشته می‌گیریم، و کوتاه‌ترین نامِ
            منطبق را برمی‌داریم تا اگر دو گروه هر دو شامل کلیدواژه
            بودند، دقیق‌ترینش انتخاب شود.
            """
            needle = key(wanted)
            hits = [g for g in groups
                    if g.pk not in taken and needle in key(g.name)]
            if not hits:
                return None
            return min(hits, key=lambda g: len(key(g.name)))

        for wanted, order in WANTED:
            group = match(wanted)
            if group is None:
                missing.append(wanted)
                continue
            taken.add(group.pk)
            changes = []
            if not group.has_graduate:
                group.has_graduate = True
                changes.append('has_graduate')
            if group.graduate_order != order:
                group.graduate_order = order
                changes.append('graduate_order')
            if changes:
                group.save(update_fields=changes)
            found.append(group.name)

        # هر گروه دیگری که پیش‌تر علامت خورده و در فهرست سند نیست.
        # مبنا `taken` است نه مقایسهٔ نام: نام واقعی گروه با کلیدواژهٔ
        # سند یکی نیست («گروه مدیریت بازرگانی» در برابر «بازرگانی»)،
        # و با مقایسهٔ نام، همان‌هایی که تازه علامت خورده بودند
        # بلافاصله برداشته می‌شدند.
        for group in groups:
            if group.pk not in taken and group.has_graduate:
                group.has_graduate = False
                group.save(update_fields=['has_graduate'])
                self.stdout.write('  برداشته شد: %s' % group.name)

        if found:
            self.stdout.write(self.style.SUCCESS(
                '%d گروه علامت خورد: %s' % (len(found), '، '.join(found))))
        if missing:
            self.stdout.write(self.style.WARNING(
                'پیدا نشد: %s' % '، '.join(missing)))
            self.stdout.write(
                'نام دقیق گروه‌های موجود را با ‎--list‎ ببینید.')
