"""رشته‌ها را با سند رسمی «رشته‌های دانشکده‌ها» هم‌خوان می‌کند.

    python manage.py set_majors_from_document --dry-run
    python manage.py set_majors_from_document

چرا لازم شد
───────────
دیتابیس ۴۷ رشتهٔ فعال داشت و سند موسسه ۴۱ ردیف دارد. بعضی نام‌ها
با سند فرق داشتند، بعضی رشته‌ها در سند بودند و در سایت نبودند، و
چند ردیف در سایت بود که در سند نیست.

سند مبناست: هر ردیفِ آن باید روی سایت باشد، زیر دانشکده و مقطعی
که خودش گفته.

با ردیف‌های اضافه چه می‌کند
───────────────────────────
غیرفعال می‌شوند، نه حذف. رشته با PROTECT به درخواست پذیرش و جدول
شهریه بسته است؛ حذف یا می‌شکند یا درخواست یک داوطلب را می‌برد.
غیرفعال‌کردن از سایت برشان می‌دارد و در پنل نگهشان می‌دارد، پس اگر
جایی اشتباه شده باشد یک تیک برمی‌گرداندش.

«حسابداری کاردانی پیوسته»
─────────────────────────
در جدول سند، این ردیف ته بلوک «فنی و مهندسی» افتاده. زیر دانشکدهٔ
مدیریت و حسابداری گذاشته شده، چون رشتهٔ حسابداری زیر دانشکدهٔ فنی
برای بازدیدکننده خطای آشکار است. اگر عمدی بوده، همین‌جا در جدول
پایین عوضش کنید.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from academics.models import AcademicGroup, Department, Major

FANNI = 'fanni-mohandesi'
MODIRIAT = 'modiriat-hesabdari'
TARBIATI = 'olum-tarbiati-ravanshenasi'

# (نام رشته، مقطع، اسلاگ دانشکده، کلیدواژهٔ گروه)
#
# کلیدواژهٔ گروه همان است که set_faculties با آن گروه‌ها را می‌شناسد؛
# رشته زیر گروهی می‌نشیند که نامش این کلیدواژه را داشته باشد.
DOCUMENT = [
    # ── دانشکده علوم تربیتی و روان‌شناسی ──
    ('علوم تربیتی - گرایش مدیریت آموزشی', 'master', TARBIATI, 'علومتربیتی'),
    ('علوم تربیتی - گرایش آموزش و پرورش ابتدایی', 'master', TARBIATI,
     'علومتربیتی'),
    ('روان‌شناسی', 'bachelor_cont', TARBIATI, 'روانشناسی'),
    # سند، جامعه‌شناسی را زیر همین دانشکده می‌آورد، نه زیر مدیریت.
    ('جامعه‌شناسی', 'bachelor_cont', TARBIATI, 'علوماجتماعی'),

    # ── دانشکده فنی و مهندسی ──
    ('مهندسی برق', 'bachelor_cont', FANNI, 'برق'),
    ('مهندسی کامپیوتر', 'bachelor_cont', FANNI, 'کامپیوتر'),
    ('مهندسی معماری', 'bachelor_cont', FANNI, 'معماری'),
    ('کاردان فنی مخابرات', 'associate_disc', FANNI, 'برق'),
    ('مهندسی تکنولوژی مخابرات - انتقال', 'bachelor_disc', FANNI, 'برق'),
    ('مهندسی حرفه‌ای برق قدرت', 'bachelor_disc', FANNI, 'برق'),
    ('مهندسی حرفه‌ای کامپیوتر نرم‌افزار', 'bachelor_disc', FANNI, 'کامپیوتر'),
    ('مهندسی حرفه‌ای معماری', 'bachelor_disc', FANNI, 'معماری'),
    ('مهندسی حرفه‌ای مکانیک خودرو', 'bachelor_disc', FANNI, 'مکانیک'),
    ('الکتروتکنیک', 'associate_cont', FANNI, 'برق'),
    ('الکترونیک و مخابرات دریایی', 'associate_cont', FANNI, 'برق'),
    ('الکترونیک عمومی', 'associate_cont', FANNI, 'برق'),
    ('کامپیوتر نرم‌افزار', 'associate_cont', FANNI, 'کامپیوتر'),
    ('مکانیک خودرو', 'associate_cont', FANNI, 'مکانیک'),
    ('معماری', 'associate_cont', FANNI, 'معماری'),
    ('نقشه‌برداری', 'associate_cont', FANNI, 'معماری'),
    ('طراحی صنعتی', 'associate_cont', FANNI, 'معماری'),
    ('فتوگرافیک گرافیک', 'associate_cont', FANNI, 'معماری'),

    # ── دانشکده مدیریت و حسابداری ──
    ('حسابداری', 'associate_cont', MODIRIAT, 'حسابداری'),
    ('حسابداری', 'master', MODIRIAT, 'حسابداری'),
    ('حسابرسی', 'master', MODIRIAT, 'حسابداری'),
    ('مدیریت بازرگانی - گرایش بازاریابی', 'master', MODIRIAT, 'مدیریتبازرگانی'),
    ('مدیریت بازرگانی - گرایش بازرگانی بین‌المللی', 'master', MODIRIAT,
     'مدیریتبازرگانی'),
    ('مدیریت صنعتی - گرایش مدیریت کیفیت و بهره‌وری', 'master', MODIRIAT,
     'مدیریتصنعتی'),
    ('مدیریت صنعتی - گرایش تولید و عملیات', 'master', MODIRIAT,
     'مدیریتصنعتی'),
    ('حسابداری', 'bachelor_cont', MODIRIAT, 'حسابداری'),
    ('مدیریت بازرگانی', 'bachelor_cont', MODIRIAT, 'مدیریتبازرگانی'),
    ('مدیریت دولتی', 'bachelor_cont', MODIRIAT, 'مدیریتبازرگانی'),
    ('مدیریت مالی', 'bachelor_cont', MODIRIAT, 'مدیریتصنعتی'),
    ('امور دولتی', 'associate_disc', MODIRIAT, 'مدیریتبازرگانی'),
    ('حسابداری', 'associate_disc', MODIRIAT, 'حسابداری'),
    ('مدیریت بازرگانی', 'associate_disc', MODIRIAT, 'مدیریتبازرگانی'),
    ('مدیریت صنعتی کاربردی', 'associate_disc', MODIRIAT, 'مدیریتصنعتی'),
    ('حسابداری', 'bachelor_disc', MODIRIAT, 'حسابداری'),
    ('مدیریت بازرگانی', 'bachelor_disc', MODIRIAT, 'مدیریتبازرگانی'),
    ('مدیریت صنعتی', 'bachelor_disc', MODIRIAT, 'مدیریتصنعتی'),
    ('مدیریت بیمه', 'bachelor_disc', MODIRIAT, 'مدیریتبازرگانی'),
]


# نام‌های قدیمی دیتابیس → نام سند.
#
# بدون این جدول، هر تفاوت نگارشی یک رشتهٔ تازه می‌ساخت و ردیف قدیمی
# را — با سرفصل PDF و ورد پیوستش — غیرفعال می‌کرد. اینجا همان ردیف
# می‌ماند و فقط نامش به آنچه سند می‌گوید عوض می‌شود.
#
# (نام در دیتابیس، مقطع در دیتابیس، نام در سند)
ALIASES = [
    # ── فنی و مهندسی ──
    ('الکتروتکنیک برق صنعتی', 'associate_cont', 'الکتروتکنیک'),
    ('الکترونیک الکترونیک عمومی', 'associate_cont', 'الکترونیک عمومی'),
    ('الکترونیک الکترونیک دریایی', 'associate_cont',
     'الکترونیک و مخابرات دریایی'),
    ('گرافیک', 'associate_cont', 'فتوگرافیک گرافیک'),
    ('معماری نقشه کشی', 'associate_cont', 'معماری'),
    ('نقشه کشی و طراحی صنعتی', 'associate_cont', 'طراحی صنعتی'),
    ('مهندسی کامپیوتر - نرم افزار', 'bachelor_cont', 'مهندسی کامپیوتر'),
    ('مهندسی برق – قدرت', 'bachelor_disc', 'مهندسی حرفه‌ای برق قدرت'),
    ('تکنولوژی مهندسی مخابرات - انتقال', 'bachelor_disc',
     'مهندسی تکنولوژی مخابرات - انتقال'),
    ('مهندسی کامپیوتر- نرم افزار', 'bachelor_disc',
     'مهندسی حرفه‌ای کامپیوتر نرم‌افزار'),
    ('مهندسی تکنولوژی معماری', 'bachelor_disc', 'مهندسی حرفه‌ای معماری'),
    ('مهندسی تکنولوژی مکانیک خودرو', 'bachelor_disc',
     'مهندسی حرفه‌ای مکانیک خودرو'),

    # ── مدیریت و حسابداری ──
    ('حسابداری - حسابداری', 'master', 'حسابداری'),
    ('حسابداری - گرایش حسابرسی', 'master', 'حسابرسی'),
    ('مدیریت بازرگانی - گرایش بازرگانی بین الملل', 'master',
     'مدیریت بازرگانی - گرایش بازرگانی بین‌المللی'),

    # ── علوم تربیتی و روان‌شناسی ──
    ('آموزش و پرورش ابتدایی', 'master',
     'علوم تربیتی - گرایش آموزش و پرورش ابتدایی'),
]

# رشته‌هایی که مقطعشان در دیتابیس اشتباه ثبت شده بود.
#
# سند این چهار را «کاردانی ناپیوسته» می‌گوید و در سایت «کاردانی
# پیوسته» بودند. بدون این جدول، هر کدام یک بار غیرفعال و یک بار از
# نو ساخته می‌شد — یعنی سرفصل و شناسهٔ قبلی‌شان از دست می‌رفت.
#
# (نام در دیتابیس، مقطع غلط، نام در سند، مقطع درست)
REGRADED = [
    ('امور دولتی', 'associate_cont', 'امور دولتی', 'associate_disc'),
    ('مدیریت بازرگانی', 'associate_cont', 'مدیریت بازرگانی',
     'associate_disc'),
    ('مدیریت صنعتی', 'associate_cont', 'مدیریت صنعتی کاربردی',
     'associate_disc'),
    ('حسابداری و بازرگانی', 'associate_cont', 'حسابداری', 'associate_disc'),
]


def fold(text: str) -> str:
    """نام رشته، بدون تفاوت‌های نوشتاری بی‌اهمیت.

    «ي» و «ك» عربی، نیم‌فاصله، خط تیره و فاصلهٔ اضافه، همه یکسان
    دیده می‌شوند — وگرنه «نرم‌افزار» و «نرم افزار» دو رشته می‌شوند.
    """
    cleaned = (text or '').replace('ي', 'ی').replace('ك', 'ک')
    cleaned = cleaned.replace('‏', '')
    for dash in ('-', '–', '—', '‌'):
        cleaned = cleaned.replace(dash, ' ')
    cleaned = cleaned.replace('گرایش', ' ')
    # فاصله‌ها کاملاً برداشته می‌شوند: «جامعه شناسی» و «جامعه‌شناسی»
    # یک رشته‌اند، و نیم‌فاصله در دیتابیس و سند یکسان نوشته نشده.
    return ''.join(cleaned.split())


def group_key(text: str) -> str:
    cleaned = fold(text)
    for word in ('گروه', 'آموزشی'):
        cleaned = cleaned.replace(word, '')
    return cleaned


class Command(BaseCommand):
    help = 'هم‌خوان کردن رشته‌ها با سند رسمی موسسه'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='فقط بگو چه می‌شود، چیزی را عوض نکن')
        parser.add_argument('--keep-extras', action='store_true',
                            help='ردیف‌های خارج از سند را غیرفعال نکن')

    def handle(self, *args, **options):
        dry = options['dry_run']

        faculties = {d.slug: d for d in Department.objects.all()}
        for slug in (FANNI, MODIRIAT, TARBIATI):
            if slug not in faculties:
                self.stdout.write(self.style.ERROR(
                    'دانشکدهٔ %s نیست — اول set_faculties را بزنید.' % slug))
                return

        groups = list(AcademicGroup.objects.filter(is_active=True))

        added = moved = renamed = 0
        matched_ids = set()

        with transaction.atomic():
            for name, degree, faculty_slug, gkey in DOCUMENT:
                faculty = faculties[faculty_slug]
                group = self._group_for(groups, gkey, faculty)
                major = self._find(name, degree, matched_ids)

                if major is None:
                    if not dry:
                        major = Major.objects.create(
                            name=name, degree=degree, department=faculty,
                            group=group, is_active=True,
                            slug=self._slug(name, degree))
                        matched_ids.add(major.pk)
                    added += 1
                    self.stdout.write('  + %s — %s' % (name, degree))
                    continue

                matched_ids.add(major.pk)
                changes = []
                if major.degree != degree:
                    major.degree = degree
                    changes.append('مقطع')
                if major.name != name:
                    major.name = name
                    changes.append('نام')
                    renamed += 1
                if major.department_id != faculty.id or (
                        group and major.group_id != group.id):
                    major.department = faculty
                    if group:
                        major.group = group
                    changes.append('جای‌گذاری')
                    moved += 1
                if not major.is_active:
                    major.is_active = True
                    changes.append('فعال‌سازی')
                if changes and not dry:
                    major.save()
                if changes:
                    self.stdout.write('  ~ %s — %s'
                                      % (name, '، '.join(changes)))

            extras = list(
                Major.objects.filter(is_active=True).exclude(pk__in=matched_ids))
            if extras and not options['keep_extras']:
                self.stdout.write('')
                self.stdout.write('خارج از سند — غیرفعال می‌شوند:')
                for major in extras:
                    self.stdout.write('  - %s (%s)'
                                      % (major.name, major.get_degree_display()))
                    if not dry:
                        major.is_active = False
                        major.save(update_fields=['is_active'])

            if dry:
                transaction.set_rollback(True)

        head = 'اگر اجرا شود:' if dry else 'انجام شد:'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(head))
        self.stdout.write('  %d رشتهٔ سند' % len(DOCUMENT))
        self.stdout.write('  %d تازه ساخته شد' % added)
        self.stdout.write('  %d نامش اصلاح شد' % renamed)
        self.stdout.write('  %d جابه‌جا شد' % moved)
        if not options['keep_extras']:
            self.stdout.write('  %d خارج از سند غیرفعال شد' % len(extras))
        if dry:
            self.stdout.write('')
            self.stdout.write('(‎--dry-run‎ بود؛ دیتابیس دست‌نخورده ماند.)')

    # ── کمکی‌ها ──────────────────────────────────────────────────
    @staticmethod
    def _group_for(groups, key: str, faculty):
        """گروهی که این کلیدواژه در نامش هست، ترجیحاً در همین دانشکده."""
        candidates = [g for g in groups if key in group_key(g.name)]
        if not candidates:
            return None
        same = [g for g in candidates if g.department_id == faculty.id]
        pool = same or candidates
        # کوتاه‌ترین نام، دقیق‌ترین تطبیق است
        return min(pool, key=lambda g: len(g.name))

    @staticmethod
    def _find(name: str, degree: str, taken: set):
        """رشتهٔ موجود با همین نام و مقطع، که قبلاً برداشته نشده.

        نام قدیمی هم از راه جدول هم‌ارزی شناخته می‌شود، تا ردیف با
        سرفصل پیوستش حفظ شود و فقط نامش عوض شود.
        """
        target = fold(name)
        alias = {(fold(old), level): fold(new)
                 for old, level, new in ALIASES}
        for major in Major.objects.filter(degree=degree):
            if major.pk in taken:
                continue
            current = fold(major.name)
            if current == target:
                return major
            if alias.get((current, degree)) == target:
                return major

        # رشته‌ای که مقطعش غلط ثبت شده — همان ردیف، با مقطع اصلاح‌شده
        for old, wrong, new, right in REGRADED:
            if right != degree or fold(new) != target:
                continue
            for major in Major.objects.filter(degree=wrong):
                if major.pk in taken:
                    continue
                if fold(major.name) == fold(old):
                    # مقطع اینجا عوض نمی‌شود: فراخوان خودش آن را
                    # می‌بیند، در فهرست تغییرات ثبت می‌کند و ذخیره
                    # می‌کند. اگر همین‌جا عوض می‌شد و نام هم یکی بود،
                    # هیچ تغییری دیده نمی‌شد و ردیف ذخیره نمی‌شد.
                    return major
        return None

    @staticmethod
    def _slug(name: str, degree: str) -> str:
        base = slugify(name, allow_unicode=True) or 'reshte'
        candidate = '%s-%s' % (base, degree)
        number = 1
        while Major.objects.filter(slug=candidate).exists():
            number += 1
            candidate = '%s-%s-%d' % (base, degree, number)
        return candidate
