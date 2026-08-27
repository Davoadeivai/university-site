"""رشته‌های تکراری را در یکی ادغام می‌کند.

    python manage.py merge_duplicate_majors --dry-run
    python manage.py merge_duplicate_majors

چرا لازم شد
───────────
ده رشته دو بار ثبت شده بودند — هر ارشد حسابداری، هر گرایش مدیریت
بازرگانی و صنعتی، علوم تربیتی، آموزش و پرورش ابتدایی، و مکانیک
خودروی کاردانی. روی صفحهٔ دانشکده‌ها هر کدام دو ردیف پشت سر هم
دیده می‌شد و داوطلب نمی‌دانست کدام را باید بزند.

چرا نمی‌شود صرفاً حذف کرد
─────────────────────────
رشته به درخواست پذیرش و جدول شهریه وصل است و هر دو با PROTECT
بسته‌اند: حذف ردیف تکراری با خطا می‌افتد و اگر هم می‌افتاد، درخواست
داوطلبی که تصادفاً ردیف دوم را انتخاب کرده بود از بین می‌رفت. پس
اول همهٔ ارجاع‌ها به ردیف ماندگار منتقل می‌شود، بعد ردیف اضافی
برداشته می‌شود.

کدام ردیف می‌ماند
─────────────────
آن‌که بیشترین محتوا را دارد (سرفصل، توضیحات، کد رشته)؛ در تساوی،
آن‌که نشانی خواناتری دارد — «مکانیک-خودرو» به‌جای
«associate_cont-2-a870f334c0» که ماشین ساخته و در نوار نشانی
مرورگر بی‌معناست؛ و در تساوی دوباره، قدیمی‌ترین.

اگر ردیف پرمحتوا نشانی ماشینی داشته باشد و ردیف حذف‌شده نشانی
خوانا، نشانی خوانا به ردیف ماندگار می‌رسد — هم محتوا می‌ماند هم
نشانی درست.
"""
from __future__ import annotations

import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import Major

# (مدل، نام فیلد) — همهٔ چیزهایی که به یک رشته اشاره می‌کنند
REFERENCES = [
    ('accounts.UserProfile', 'major'),
    ('academics.Course', 'major'),
    ('admissions.Application', 'desired_major'),
    ('admissions.Application', 'desired_major2'),
    ('admissions.TuitionStructure', 'major'),
    ('academics.CurriculumDocument', 'major'),
]

# فیلدهایی که «پر بودن»شان نشانهٔ کامل‌تر بودن ردیف است
RICH = ['description', 'job_market', 'objectives', 'curriculum',
        'curriculum_pdf', 'curriculum_word', 'code', 'admission_requirements']


def norm(text: str) -> str:
    """نام رشته، بدون تفاوت‌های نوشتاری بی‌اهمیت."""
    cleaned = (text or '').replace('ي', 'ی').replace('ك', 'ک')
    cleaned = cleaned.replace('‌', '').replace('‏', '')
    cleaned = cleaned.replace('-', ' ').replace('–', ' ')
    return ' '.join(cleaned.split())


def richness(major: Major) -> int:
    return sum(1 for name in RICH if getattr(major, name, None))


#     master-2-1cd86017c0 — نشانی‌ای که هنگام درون‌ریزی ساخته شده
AUTO_SLUG = re.compile(r'^[a-z_]+-\d+-[0-9a-f]{6,}$')


def readable(major: Major) -> int:
    """۱ اگر نشانی رشته دست‌ساز و خوانا باشد، ۰ اگر ماشین ساخته باشد."""
    return 0 if AUTO_SLUG.match(major.slug or '') else 1


class Command(BaseCommand):
    help = 'ادغام رشته‌های تکراری (هم‌نام و هم‌مقطع)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')

    def handle(self, *args, **options):
        dry = options['dry_run']

        buckets = defaultdict(list)
        for major in Major.objects.all().order_by('pk'):
            buckets[(norm(major.name), major.degree)].append(major)

        duplicates = {k: v for k, v in buckets.items() if len(v) > 1}
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('رشتهٔ تکراری‌ای نیست.'))
            return

        merged = moved = 0
        with transaction.atomic():
            for (name, _degree), rows in sorted(duplicates.items()):
                keeper = max(
                    rows, key=lambda m: (richness(m), readable(m), -m.pk))
                extras = [m for m in rows if m.pk != keeper.pk]
                self.stdout.write('  %s — %d ردیف، %s می‌ماند'
                                  % (name, len(rows), keeper.slug))
                spare = next((m.slug for m in extras if readable(m)), '')
                for extra in extras:
                    moved += self._repoint(extra, keeper, dry)
                    if not dry:
                        extra.delete()
                    merged += 1
                if spare and not readable(keeper):
                    self.stdout.write('     نشانی: %s ← %s'
                                      % (spare, keeper.slug))
                    keeper.slug = spare
                    if not dry:
                        keeper.save(update_fields=['slug'])
            if dry:
                transaction.set_rollback(True)

        head = 'اگر اجرا شود:' if dry else 'انجام شد:'
        self.stdout.write(self.style.SUCCESS(head))
        self.stdout.write('  %d رشتهٔ تکراری برداشته شد' % merged)
        self.stdout.write('  %d ارجاع منتقل شد' % moved)
        if dry:
            self.stdout.write('')
            self.stdout.write('(‎--dry-run‎ بود؛ دیتابیس دست‌نخورده ماند.)')

    def _repoint(self, extra: Major, keeper: Major, dry: bool) -> int:
        """هر چیزی که به ردیف اضافی اشاره می‌کند، به ردیف ماندگار بچسبد."""
        from django.apps import apps

        moved = 0
        for label, field in REFERENCES:
            try:
                model = apps.get_model(label)
            except LookupError:
                continue
            rows = list(model.objects.filter(**{field: extra}))
            for row in rows:
                if self._would_clash(model, field, row, keeper):
                    # جدول شهریه روی (رشته، سال) یکتاست: ردیف تکراری
                    # را جابه‌جا نمی‌کنیم، برمی‌داریم — همان عدد از
                    # قبل زیر ردیف ماندگار هست.
                    if not dry:
                        row.delete()
                    continue
                setattr(row, field, keeper)
                if not dry:
                    row.save(update_fields=[field])
                moved += 1
        return moved

    @staticmethod
    def _would_clash(model, field, row, keeper) -> bool:
        for combo in model._meta.unique_together:
            if field not in combo:
                continue
            lookup = {}
            for name in combo:
                lookup[name] = keeper if name == field else getattr(row, name)
            if model.objects.filter(**lookup).exclude(pk=row.pk).exists():
                return True
        return False
