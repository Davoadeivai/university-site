"""ساخت پروندهٔ استاد از روی «افراد موسسه».

چرا لازم است
────────────
`directory.DirectoryPerson` فهرست خام سند رسمی است: ۱۲ عضو هیات علمی،
۱۰ مدیر گروه و ۴۳ مدرس. ولی صفحهٔ عمومی «اساتید» از `faculty.Professor`
می‌خواند و آن جدول صفر رکورد دارد — یعنی سایت ۵۵ نفر عضو علمی دارد و
صفحهٔ اساتیدش خالی است.

این دستور همان آدم‌ها را در `Professor` می‌سازد تا صفحه پر شود، و
`DirectoryPerson` را دست نمی‌زند: آن همچنان فهرست سند می‌ماند و با
`seed_directory` تازه می‌شود.

چه چیزی حدس زده می‌شود
──────────────────────
اگر در «افراد موسسه» مرتبهٔ علمی صریح نوشته شده باشد، همان حکم است و
حدسی در کار نیست — و اگر پروندهٔ استاد از قبل مرتبهٔ دیگری داشته
باشد، همین حکم جایش می‌نشیند.

فقط وقتی خالی باشد از مدرک استنتاج می‌شود: دکتری → استادیار، ارشد →
مربی. این قرارداد رایج است ولی حکم رسمی نیست — دانشیار و استاد تمام
هیچ‌وقت از دلِ آن بیرون نمی‌آیند. خروجی دستور همه را فهرست می‌کند تا
در پنل بررسی شوند. با `--draft` همه غیرفعال ساخته می‌شوند تا پیش از
تأیید روی سایت نیایند.
"""
from __future__ import annotations

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from directory.models import DirectoryPerson
from faculty.models import Professor

# دسته‌های `DirectoryPerson` که استاد محسوب می‌شوند، با وضعیت استخدامی.
# ترتیب مهم است: کسی که هم مدیر گروه است و هم مدرس، باید تمام‌وقت
# ثبت شود نه نیمه‌وقت، پس دستهٔ قوی‌تر اول می‌آید.
SOURCES = [
    ('faculty', 'full_time'),
    ('group_head', 'full_time'),
    ('lecturer', 'part_time'),
]

# مدرک → مرتبهٔ علمی. حدس است، نه حکم؛ خروجی هشدار می‌دهد.
RANK_BY_DEGREE = {
    'phd': 'assistant',      # استادیار
    'ms': 'instructor',      # مربی
    'bs': 'instructor',
    '': 'instructor',
}

# نام‌هایی که تنها نمی‌آیند و همیشه بخشی از نام کوچک‌اند
COMPOUND_FIRST = {'سید', 'سیده', 'ام‌البنین', 'ام البنین', 'شیخ', 'حاج'}

# پیشوندهایی که در فارسی فقط برای دارندهٔ دکتری به کار می‌روند
DOCTOR_TITLES = {'دکتر', 'دكتر'}


def known_degree(full_name: str, fallback: str = '') -> str:
    """مدرک را از همهٔ جاهایی که این نام آمده جمع می‌کند.

    جدول‌های سند یکدست نیستند: «حسن فارسیجانی» در فهرست مدیران گروه
    بدون مدرک آمده ولی در دفترچهٔ پرسنل پیشوند «دکتر» دارد. بدون این،
    رئیس موسسه روی صفحهٔ اساتید «مربی» ثبت می‌شد — که از خالی‌بودن
    صفحه هم بدتر است.
    """
    rows = DirectoryPerson.objects.filter(full_name=full_name)
    for row in rows:
        if row.degree:
            return row.degree
    for row in rows:
        if (row.honorific or '').strip() in DOCTOR_TITLES:
            return 'phd'
    return fallback


def split_name(full_name: str) -> tuple[str, str]:
    """«سیده مریم بابانژاد باقری» → («سیده مریم», «بابانژاد باقری»).

    فارسی قاعدهٔ قطعی ندارد و «علی اکبر جعفری» با همین قاعده به
    «علی» + «اکبر جعفری» می‌شکند که دقیق نیست. مهم نیست: صفحهٔ عمومی
    نام و نام خانوادگی را کنار هم چاپ می‌کند، پس آنچه بازدیدکننده
    می‌بیند درست است و فقط مرتب‌سازی الفبایی ممکن است جابه‌جا شود.
    ادمین می‌تواند اصلاحش کند.
    """
    parts = (full_name or '').split()
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    take = 2 if (parts[0] in COMPOUND_FIRST and len(parts) >= 3) else 1
    return ' '.join(parts[:take]), ' '.join(parts[take:])


def unique_slug(base: str, taken: set) -> str:
    slug = slugify(base, allow_unicode=True) or 'ostad'
    candidate, index = slug, 2
    while candidate in taken:
        candidate = '%s-%d' % (slug, index)
        index += 1
    taken.add(candidate)
    return candidate


class Command(BaseCommand):
    help = 'ساخت رکورد استاد از روی افراد موسسه (هیات علمی، مدیران گروه، مدرسین)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--draft', action='store_true',
            help='همه را غیرفعال بساز تا پیش از تأیید روی سایت نیایند',
        )
        parser.add_argument(
            '--skip-lecturers', action='store_true',
            help='فقط هیات علمی و مدیران گروه؛ ۴۳ مدرس وارد نشوند',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='فقط گزارش بده، چیزی ننویس',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options['dry_run']
        sources = [s for s in SOURCES
                   if not (options['skip_lecturers'] and s[0] == 'lecturer')]

        taken = set(Professor.objects.values_list('slug', flat=True))
        created = updated = 0
        merged: list[str] = []
        seen: dict[tuple, Professor] = {}
        report: list[tuple] = []

        for category, status in sources:
            people = DirectoryPerson.objects.filter(
                category=category, is_active=True).order_by('order', 'full_name')

            for person in people:
                first, last = split_name(person.full_name)
                key = (first, last)

                if key in seen:
                    # همان آدم در دستهٔ قبلی هم بود — مثلاً مدیر گروهی
                    # که عضو هیات علمی هم هست. رکورد تازه نمی‌سازیم.
                    merged.append('%s (%s)' % (
                        person.full_name, person.get_category_display()))
                    continue

                degree = known_degree(person.full_name, person.degree or '')
                # مرتبهٔ صریحِ سند بر حدس مقدم است
                stated = (person.academic_rank or '').strip()
                rank = stated or RANK_BY_DEGREE.get(degree, 'instructor')
                defaults = {
                    'rank': rank,
                    'status': status,
                    'specialization': person.field_of_study or '',
                    'email': person.email or '',
                    'phone': person.phone or (
                        'داخلی %s' % person.extension if person.extension else ''),
                    'is_active': not options['draft'],
                }

                if dry:
                    exists = Professor.objects.filter(
                        first_name=first, last_name=last).exists()
                    created += not exists
                    updated += exists
                    seen[key] = None
                    report.append((person.full_name, first, last, rank, status,
                                   bool(person.photo)))
                    continue

                professor = Professor.objects.filter(
                    first_name=first, last_name=last).first()
                if professor is None:
                    defaults['slug'] = unique_slug(
                        '%s %s' % (first, last), taken)
                    professor = Professor.objects.create(
                        first_name=first, last_name=last, **defaults)
                    created += 1
                else:
                    # فیلدهایی که ادمین پر کرده بازنویسی نمی‌شوند؛
                    # فقط جاهای خالی از سند پر می‌شوند.
                    for field, value in defaults.items():
                        if value and not getattr(professor, field, None):
                            setattr(professor, field, value)
                    # مرتبهٔ صریح استثناست: وقتی موسسه در «افراد
                    # موسسه» نوشته «دانشیار»، حدسِ قبلیِ همین دستور
                    # («استادیار») باید کنار برود، وگرنه اصلاح در
                    # پنل هیچ‌وقت به پروندهٔ استاد نمی‌رسد.
                    if stated and professor.rank != stated:
                        professor.rank = stated
                    professor.save()
                    updated += 1

                if person.photo and not professor.photo:
                    try:
                        person.photo.open('rb')
                        professor.photo.save(
                            person.photo.name.rsplit('/', 1)[-1],
                            ContentFile(person.photo.read()), save=True)
                    except (OSError, ValueError) as exc:
                        self.stderr.write('  عکس %s منتقل نشد (%s)'
                                          % (person.full_name, type(exc).__name__))
                    finally:
                        try:
                            person.photo.close()
                        except (OSError, ValueError):
                            pass

                seen[key] = professor
                report.append((person.full_name, first, last, rank, status,
                               bool(person.photo)))

        # ── گزارش ─────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write('%-30s %-16s %-14s %-12s %s' % (
            'نام کامل', 'نام', 'نام خانوادگی', 'مرتبه', 'عکس'))
        self.stdout.write('─' * 84)
        for full, first, last, rank, status, has_photo in report:
            self.stdout.write('%-30s %-16s %-14s %-12s %s' % (
                full[:29], first[:15], last[:13],
                dict(Professor.RANK_CHOICES)[rank], '✓' if has_photo else '—'))

        verb = 'می‌شد ساخت' if dry else 'ساخته شد'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '%d استاد %s، %d به‌روز شد.' % (created, verb, updated)))

        if merged:
            self.stdout.write(
                '\n%d نفر در بیش از یک دسته بودند و یک‌بار ثبت شدند:' % len(merged))
            for line in merged:
                self.stdout.write('  - %s' % line)

        self.stdout.write(self.style.WARNING(
            '\n⚠ «مرتبه علمی» در سند نبود و از روی مدرک حدس زده شد '
            '(دکتری → استادیار، ارشد → مربی).'))
        self.stdout.write(
            '  در پنل ادمین ← اساتید، مرتبهٔ واقعی هر نفر را بررسی کنید.')
        self.stdout.write(
            '  «دانشکده»، بیوگرافی و زمینهٔ پژوهشی هم خالی مانده‌اند؛ '
            'سند این‌ها را نداشت.')

        if options['draft']:
            self.stdout.write(self.style.WARNING(
                '\nهمه غیرفعال ساخته شدند — تا در پنل فعالشان نکنید روی '
                'سایت دیده نمی‌شوند.'))
        if dry:
            self.stdout.write('\nحالت آزمایشی بود — چیزی نوشته نشد.')
