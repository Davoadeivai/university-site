"""گزارش وضعیت هجده بند سند اصلاحات موسسه.

    python manage.py check_revisions

چرا این دستور هست
─────────────────
«در کد هست» با «روی سایت اعمال شده» یکی نیست: کد باید کپی شود،
مهاجرت بخورد، فایل ثابت جمع شود، و بعضی بندها به دادهٔ پنل هم
وابسته‌اند. تا امروز تنها راه فهمیدنش باز کردن صفحه‌به‌صفحهٔ سایت
بود.

این دستور هر بند را روی همان چیزی می‌سنجد که کاربر می‌بیند —
قالبِ نصب‌شده و ردیف‌های دیتابیس — نه روی مخزن گیت. پس اگر
deploy.py اجرا نشده باشد، همین‌جا معلوم می‌شود.

هیچ چیزی را عوض نمی‌کند؛ فقط می‌خواند.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

DONE, MISSING, MANUAL = 'done', 'missing', 'manual'


class Command(BaseCommand):
    help = 'وضعیت بندهای سند اصلاحات موسسه'

    # ── کمکی‌ها ──────────────────────────────────────────────────
    def _template(self, name: str) -> str:
        path = Path(settings.BASE_DIR) / 'templates' / name
        try:
            return path.read_text(encoding='utf-8')
        except OSError:
            return ''

    def _css(self) -> str:
        path = Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css'
        try:
            return path.read_text(encoding='utf-8')
        except OSError:
            return ''

    # ── بندها ────────────────────────────────────────────────────
    def _checks(self) -> list:
        from core.models import PresidencyOffice, SiteSettings
        from academics.models import AcademicGroup

        base = self._template('base.html')
        presidency = self._template('core/presidency.html')
        groups = self._template('academics/groups_list.html')
        css = self._css()

        office = PresidencyOffice.objects.first()
        site = SiteSettings.objects.first()

        def has(text, where=base):
            return DONE if text in where else MISSING

        rows = []

        rows.append((1, 'اسلایدهای صفحه اول', MANUAL,
                     'تصاویر و متن‌ها را موسسه باید بدهد'))

        photo = bool(office and office.president_photo)
        # رزومه حالا یک فایل قابل دانلود است، نه شش کارت روی صفحه
        resume = bool(office and office.president_cv)
        website = bool(office and office.president_website)
        rows.append((
            2, 'صفحهٔ ریاست: عکس، نشان، رزومه، نشانی',
            DONE if (photo and resume and website) else MISSING,
            'عکس=%s رزومه=%s نشانی=%s' % (
                'دارد' if photo else 'ندارد',
                'فایل دارد' if resume else 'فایل آپلود نشده — پنل ← دفتر ریاست',
                'دارد' if website else 'ندارد')))

        rows.append((3, 'فونت Arial و درشت‌تر در سربرگ',
                     has("font-family: Arial", css),
                     'قاعدهٔ .bnr-fa در main.css'))

        rows.append((4, 'حذف شعار «دانش · مهارت · آینده»',
                     MISSING if 'دانش · مهارت · آینده' in base else DONE,
                     'در base.html نباشد'))

        in_template = 'bnr-wcu' in base
        uploaded = bool(site and site.world_class_logo)
        rows.append((
            5, 'نشان کلاس جهانی در دو سوی نام',
            DONE if (in_template and uploaded) else MISSING,
            'قالب=%s آپلود=%s' % (
                'دارد' if in_template else 'ندارد',
                'شده' if uploaded else 'نشده — پنل ← تنظیمات سایت')))

        rows.append((6, 'رنگ‌بندی و محور تایم‌لاین تقویم',
                     DONE if 'calendar_ink' in str(
                         [f.name for f in SiteSettings._meta.fields]) else MISSING,
                     'رنگ‌ها از پنل قابل تنظیم است؛ «محور» هنوز مشخص نشده'))

        rows.append((7, 'رنگ‌بندی و بک‌گراند سایت', MANUAL,
                     'رنگ موردنظر موسسه اعلام نشده'))

        chart = bool(site and site.org_chart_file)
        rows.append((
            8, 'چارت سازمانی',
            DONE if chart else MISSING,
            ('فایل هست + نمایش تمام‌صفحه'
             if chart and 'data-zoomable' in self._template('core/about.html')
             else 'فایل آپلود نشده — پنل ← تنظیمات سایت')))

        clean = ('pres-tile-1' in presidency
                 and 'افزودن به مخاطبان' not in presidency
                 and 'president_message' not in presidency)
        rows.append((9, 'صفحهٔ ریاست: فقط ارتباط، افقی و رنگی',
                     DONE if clean else MISSING,
                     'کارت‌های رنگی افقی، بدون پیام و معرفی و vCard'))

        rows.append((10, 'رنگ و فونت اعضای هیئت امنا',
                     has('board-name', self._template('core/board_trustees.html')),
                     'نام‌ها جدا از سمت‌ها'))

        rows.append((11, '«هیئت علمی» به‌جای «اعضای موسسه»',
                     DONE if ('هیئت علمی' in base
                              and 'هیات امنا' not in base) else MISSING,
                     'و حذف هیئت امنا و موسس از منو'))

        rows.append((12, 'مدیر گروه در کارت گروه‌های آموزشی',
                     has('grp-head-photo', groups),
                     'عکس و نام مدیر گروه'))

        # ساختار از core/vices.py می‌آید؛ همان را می‌سنجیم، نه متن
        # قالب. شماره‌ها حالا در <span> جدا هستند و جست‌وجوی
        # «۱. معاونت» دیگر چیزی پیدا نمی‌کند.
        from core.vices import VICE_ORDER
        expected = ['education', 'research', 'admin_finance',
                    'student', 'construction']
        order = [key for key, _label, _icon in VICE_ORDER] == expected
        looped = 'nav_vices' in base
        rows.append((13, 'منوی معاونت‌ها با ترتیب سند',
                     DONE if (order and looped) else MISSING,
                     'آموزشی، پژوهشی، اداری‌ومالی، دانشجویی، فنی‌وعمرانی'))

        # لنگر باید خودِ آیتم منو باشد: اولین «معاونت پژوهشی» در
        # base.html داخل یک کامنت است و بلوکِ بعدش منو نیست.
        from core.vices import STATIC_UNITS
        research_block = str(STATIC_UNITS.get('research', []))
        rows.append((14, 'دفتر همکاری‌های علمی زیر معاونت پژوهشی',
                     DONE if 'international_office' in research_block else MISSING,
                     'و برداشته‌شده از حوزهٔ ریاست'))

        rows.append((15, 'زیرمجموعهٔ هر معاونت در منو',
                     has('nav-dd-sub'),
                     'بر اساس چارت سازمانی'))

        top_level = base.count('nav-link-flat') and 'تحصیلات تکمیلی' in base
        education_block = str(STATIC_UNITS.get('education', []))
        rows.append((
            16, 'تحصیلات تکمیلی زیر معاونت آموزشی',
            DONE if 'graduate_studies' in education_block else MISSING,
            'و حذف از منوهای اصلی' if top_level else ''))

        graduate = list(AcademicGroup.objects.filter(
            has_graduate=True).order_by('graduate_order', 'name')
            .values_list('name', flat=True)) \
            if hasattr(AcademicGroup, 'has_graduate') else []
        rows.append((
            17, 'چهار گروه دارای تحصیلات تکمیلی',
            DONE if len(graduate) >= 4 else MISSING,
            '، '.join(graduate) if graduate else 'هیچ گروهی علامت نخورده'))

        from core.models import VicePresidency
        # نام مدیر گروه در فیلد head است، نه head_name
        heads = AcademicGroup.objects.exclude(head='').count()
        head_gap = AcademicGroup.objects.exclude(head='').exclude(
            head__startswith='دکتر').count()
        vices = VicePresidency.objects.exclude(full_name='').count()
        vice_gap = VicePresidency.objects.exclude(full_name='').exclude(
            full_name__startswith='دکتر').count()
        total_groups = AcademicGroup.objects.filter(is_active=True).count()
        # «۰ مدیر گروه، ۰ بدون عنوان» یک ✓ توخالی است: سند نام مدیران
        # را خواسته و اینجا اصلاً نامی ثبت نشده. تیک‌خوردنِ چیزی که
        # وجود ندارد، بدتر از گزارش نکردنش است.
        empty = total_groups and not heads
        rows.append((
            18, '«دکتر» پیش از نام مدیران و معاونان',
            MISSING if (empty or head_gap + vice_gap) else DONE,
            ('نام هیچ‌یک از %d مدیر گروه ثبت نشده — پنل ← گروه‌های آموزشی'
             % total_groups) if empty else
            '%d مدیر گروه (%d بدون عنوان)، %d معاون (%d بدون عنوان)' % (
                heads, head_gap, vices, vice_gap)))

        return rows

    # ── اجرا ─────────────────────────────────────────────────────
    def handle(self, *args, **options):
        marks = {
            DONE: (self.style.SUCCESS, '✓'),
            MISSING: (self.style.ERROR, '✗'),
            MANUAL: (self.style.WARNING, '…'),
        }

        try:
            rows = self._checks()
        except Exception as exc:                    # noqa: BLE001
            self.stdout.write(self.style.ERROR('بازرسی ناتمام ماند: %s' % exc))
            self.stdout.write(
                'اگر خطا دربارهٔ ستون یا فیلد است، یعنی migrate اجرا نشده.')
            return

        self.stdout.write('=' * 62)
        self.stdout.write('وضعیت بندهای سند اصلاحات')
        self.stdout.write('=' * 62)

        tally = {DONE: 0, MISSING: 0, MANUAL: 0}
        for number, title, state, note in rows:
            tally[state] += 1
            style, mark = marks[state]
            self.stdout.write(style('%s %2d. %s' % (mark, number, title)))
            if note:
                self.stdout.write('      %s' % note)

        self.stdout.write('')
        self.stdout.write(
            '%d انجام‌شده، %d ناتمام، %d منتظر موسسه — از %d بند.' % (
                tally[DONE], tally[MISSING], tally[MANUAL], len(rows)))

        if tally[MISSING]:
            self.stdout.write('')
            self.stdout.write(
                'بندهای ✗ یا به دیپلوی نیاز دارند یا به یک آپلود در پنل؛ '
                'یادداشت زیر هرکدام می‌گوید کدام.')
