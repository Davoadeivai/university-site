"""گزارش می‌دهد کدام گروه آموزشی هنوز مدیر ندارد.

    python manage.py check_group_heads
    python manage.py check_group_heads --suggest

چرا لازم شد
───────────
یازده گروه آموزشی هست و هیچ‌کدام مدیرش ثبت نشده بود. روی صفحهٔ
گروه‌ها جای کارت مدیر خالی می‌ماند و بازدیدکننده نمی‌داند با چه
کسی طرف است.

با ‎--suggest‎، از میان اعضای هیئت علمی همان دانشکده چند نام
پیشنهاد می‌دهد تا انتخاب در پنل آسان‌تر شود. پیشنهاد است، نه
تصمیم: هیچ‌چیزی خودکار ثبت نمی‌شود، چون «مدیر گروه کیست» را فقط
موسسه می‌داند.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from academics.models import AcademicGroup


class Command(BaseCommand):
    help = 'گزارش گروه‌های بدون مدیر'

    def add_arguments(self, parser):
        parser.add_argument(
            '--suggest', action='store_true',
            help='اعضای هیئت علمی همان دانشکده را پیشنهاد بده')

    def handle(self, *args, **options):
        groups = (AcademicGroup.objects.filter(is_active=True)
                  .select_related('department', 'head_professor')
                  .order_by('order', 'name'))
        if not groups:
            self.stdout.write(self.style.WARNING('گروهی ثبت نشده.'))
            return

        linked = manual = missing = 0
        for group in groups:
            if group.head_professor_id:
                linked += 1
                self.stdout.write(self.style.SUCCESS(
                    '  ✓ %-34s %s' % (group.name, group.head_name)))
            elif group.head:
                manual += 1
                self.stdout.write(
                    '  ~ %-34s %s  (دستی — به پروندهٔ هیئت علمی وصل نیست)'
                    % (group.name, group.head))
            else:
                missing += 1
                self.stdout.write(self.style.WARNING(
                    '  ✗ %-34s — ثبت نشده' % group.name))
                if options['suggest']:
                    self._suggest(group)

        self.stdout.write('')
        self.stdout.write('از %d گروه:' % len(groups))
        self.stdout.write('  %d به پروندهٔ هیئت علمی وصل' % linked)
        if manual:
            self.stdout.write('  %d دستی نوشته شده' % manual)
        if missing:
            self.stdout.write(self.style.WARNING(
                '  %d بدون مدیر' % missing))
            self.stdout.write('')
            self.stdout.write('ثبت از پنل: گروه‌های آموزشی ← گروه ← '
                              'بخش «مدیر گروه»')

    def _suggest(self, group):
        """چند عضو هیئت علمی از همان دانشکده."""
        from faculty.models import Professor

        if not group.department_id:
            return
        # مرتبهٔ بالاتر اول: مدیر گروه معمولاً از میان همین‌هاست
        order = {'professor': 0, 'associate': 1, 'assistant': 2,
                 'instructor': 3, 'emeritus': 4}
        people = sorted(
            Professor.objects.filter(department_id=group.department_id)[:12],
            key=lambda p: order.get(p.rank, 9))
        for person in people[:3]:
            self.stdout.write('        پیشنهاد: %s (%s)'
                              % (person.get_full_name(),
                                 person.get_rank_display()))
