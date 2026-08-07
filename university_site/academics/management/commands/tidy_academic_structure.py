"""مرتب‌کردن ساختار آموزشی: گروه هر رشته، و حذف رکوردهای آزمایشی.

مسئله
─────
سایت دو «دانشکده» دارد — `bargh` با صفر رشته، و «تحصیلات تکمیلی» که
هر ۵۸ رشته زیرش نشسته، از کاردانی گرافیک تا ارشد حسابداری. یعنی
صفحهٔ عمومی به داوطلب کاردانی می‌گوید رشته‌اش زیر دانشکدهٔ تحصیلات
تکمیلی است.

واحد واقعی این موسسه «گروه آموزشی» است، نه دانشکده: ۱۱ گروه با توزیع
درست (بازرگانی ۱۰ رشته، برق ۹، معماری ۶ …). دانشکده یک لایهٔ خالی
است که فقط اشتباه را نمایش می‌دهد.

این دستور دو کار می‌کند:
  ۱. رشته‌های بی‌گروه را از روی نامشان به گروه درست وصل می‌کند
  ۲. رکوردهای آزمایشیِ بدون رشته (مثل `bargh`) را حذف می‌کند

`Department` حذف نمی‌شود — کلید خارجی‌اش اجباری است و برداشتنش
مهاجرت پرریسکی می‌خواهد. به‌جایش از صفحه‌های عمومی برداشته شده.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import AcademicGroup, Department, Major

# کلیدواژهٔ نام رشته → بخشی از نام گروه. ترتیب مهم است: خاص پیش از عام،
# وگرنه «مدیریت بازرگانی» با قاعدهٔ «مدیریت» به گروه اشتباه می‌رود.
GROUP_HINTS = [
    ('حسابرس', 'حسابداری'),
    ('حسابدار', 'حسابداری'),
    ('بازرگانی', 'مدیریت بازرگانی'),
    ('بیمه', 'مدیریت بازرگانی'),
    ('صنعتی', 'مدیریت صنعتی'),
    ('مدیریت مالی', 'مدیریت صنعتی'),
    ('مدیریت دولتی', 'مدیریت بازرگانی'),
    ('امور دولتی', 'مدیریت بازرگانی'),
    ('تربیتی', 'علوم تربیتی'),
    ('آموزش و پرورش', 'علوم تربیتی'),
    ('مدیریت آموزشی', 'علوم تربیتی'),
    ('روانشناس', 'روانشناسی'),
    ('مشاوره', 'روانشناسی'),
    ('جامعه', 'علوم اجتماعی'),
    ('کامپیوتر', 'کامپیوتر'),
    ('نرم افزار', 'کامپیوتر'),
    ('الکترو', 'برق'),
    ('مخابرات', 'برق'),
    ('برق', 'برق'),
    ('خودرو', 'مکانیک'),
    ('مکانیک', 'مکانیک'),
    ('نقشه', 'معماری'),
    ('معماری', 'معماری'),
    ('گرافیک', 'معماری'),
]


def guess_group(name: str):
    for keyword, part in GROUP_HINTS:
        if keyword in (name or ''):
            group = AcademicGroup.objects.filter(name__icontains=part).first()
            if group:
                return group
    return None


class Command(BaseCommand):
    help = 'وصل‌کردن رشته‌های بی‌گروه و حذف رکوردهای آزمایشی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='فقط گزارش بده')
        parser.add_argument(
            '--purge-empty', action='store_true',
            help='گروه و دانشکدهٔ بدون هیچ رشته‌ای را حذف کن — برای '
                 'رکوردهای آزمایشی مثل «bargh».')

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options['dry_run']

        # ── ۱) رشته‌های بی‌گروه ──
        orphans = Major.objects.filter(group__isnull=True)
        linked, unresolved = 0, []
        for major in orphans:
            group = guess_group(major.name)
            if group is None:
                unresolved.append('%s (%s)' % (major.name, major.get_degree_display()))
                continue
            self.stdout.write('  %-42s → %s' % (major.name[:41], group.name))
            if not dry:
                major.group = group
                major.save(update_fields=['group'])
            linked += 1

        verb = 'می‌شد وصل کرد' if dry else 'وصل شد'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '%d رشته به گروه %s.' % (linked, verb)))
        if unresolved:
            self.stdout.write(self.style.WARNING(
                '%d رشته گروهش معلوم نشد — در پنل انتخابش کنید:'
                % len(unresolved)))
            for line in unresolved:
                self.stdout.write('  - %s' % line)

        # ── ۲) رکوردهای خالی ──
        empty_groups = [g for g in AcademicGroup.objects.all()
                        if not g.majors.exists()]
        empty_depts = [d for d in Department.objects.all()
                       if not d.majors.exists() and not d.groups.exists()]

        if empty_groups or empty_depts:
            self.stdout.write('')
            self.stdout.write('گروه/دانشکدهٔ بدون هیچ رشته‌ای:')
            for g in empty_groups:
                self.stdout.write('  گروه:     %s' % g.name)
            for d in empty_depts:
                self.stdout.write('  دانشکده:  %s' % d.name)

            if options['purge_empty'] and not dry:
                # فقط آن‌هایی که نامشان هم بی‌معناست؛ گروه واقعیِ
                # خالی ممکن است رشته‌اش هنوز ثبت نشده باشد و حذفش
                # کار ادمین را از بین می‌برد.
                removed = 0
                for g in empty_groups:
                    if not any('؀' <= ch <= 'ۿ' for ch in g.name):
                        self.stdout.write('  حذف گروه: %s' % g.name)
                        g.delete()
                        removed += 1
                for d in empty_depts:
                    if not any('؀' <= ch <= 'ۿ' for ch in d.name):
                        self.stdout.write('  حذف دانشکده: %s' % d.name)
                        d.delete()
                        removed += 1
                self.stdout.write(self.style.SUCCESS(
                    '%d رکورد آزمایشی حذف شد.' % removed))
                if len(empty_groups) + len(empty_depts) > removed:
                    self.stdout.write(
                        'بقیه نام فارسی دارند و دست‌نخورده ماندند — '
                        'شاید رشته‌شان هنوز ثبت نشده.')
            elif not options['purge_empty']:
                self.stdout.write(
                    'برای حذف رکوردهای بی‌نام‌ونشان، --purge-empty بزنید.')

        if dry:
            self.stdout.write('\nحالت آزمایشی بود — چیزی نوشته نشد.')
