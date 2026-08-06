"""تست‌های هویت بصری و تقویم آموزشی.

اجرا:  python manage.py test core
"""
import base64
import os
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academics.models import AcademicCalendar
from core.academic_timeline import build_timeline
from core.models import PresidencyOffice, SecurityOffice

INSTITUTE = 'موسسه آموزش عالی علامه امینی'
# نام موسسه هرگز نباید پسوند شهر بگیرد — نه شکل قدیمی، نه شکل تازه
FORBIDDEN_SUFFIXES = ('علامه امینی بهنمیر', 'علامه امینی - بهنمیر',
                      'علامه امینی بابلسر', 'علامه امینی - بابلسر')


class BrandNameTests(TestCase):
    """نام موسسه همه‌جا دقیقاً «موسسه آموزش عالی علامه امینی» است."""

    def test_home_uses_new_name_only(self):
        res = self.client.get(reverse('core:home'))
        body = res.content.decode()
        self.assertEqual(res.status_code, 200)
        self.assertIn(INSTITUTE, body)
        for bad in FORBIDDEN_SUFFIXES:
            self.assertNotIn(bad, body, 'نام موسسه پسوند شهر گرفته: %s' % bad)

    def test_no_page_appends_a_city_to_the_name(self):
        """چند صفحهٔ پرتردد: نام باید بدون دنبالهٔ شهر باشد."""
        for name in ('core:home', 'core:about', 'contact:contact',
                     'core:documents', 'accounts:login'):
            body = self.client.get(reverse(name)).content.decode()
            for bad in FORBIDDEN_SUFFIXES:
                self.assertNotIn(bad, body, '%s → %s' % (name, bad))

    def test_banner_is_live_text_not_an_image(self):
        body = self.client.get(reverse('core:home')).content.decode()
        # نام باید متن باشد تا سئو و screen reader بخوانندش
        self.assertIn('class="bnr-fa"', body)
        # بنر تصویری قدیمی که نام داخلش پخته بود
        self.assertNotIn('banner-complete-786x86.png', body)
        # نشان‌ها دارایی جدا هستند
        self.assertIn('mark-institute.png', body)
        self.assertIn('mark-iran.png', body)

    def test_login_page_uses_new_name(self):
        body = self.client.get(reverse('accounts:login')).content.decode()
        for bad in FORBIDDEN_SUFFIXES:
            self.assertNotIn(bad, body)


class AcademicTimelineTests(TestCase):
    """وضعیت زندهٔ مراحل — چیزی که یک تصویر ثابت نمی‌تواند بدهد."""

    def setUp(self):
        self.today = timezone.localdate()
        self.year = '1405-1406'
        mk = AcademicCalendar.objects.create
        mk(title='گذشته', academic_year=self.year, semester='fall',
           start_date=self.today - timedelta(days=30),
           end_date=self.today - timedelta(days=25))
        mk(title='در جریان', academic_year=self.year, semester='fall',
           start_date=self.today - timedelta(days=2),
           end_date=self.today + timedelta(days=2))
        mk(title='بعدی', academic_year=self.year, semester='fall',
           start_date=self.today + timedelta(days=10),
           end_date=self.today + timedelta(days=10))
        mk(title='دورتر', academic_year=self.year, semester='fall',
           start_date=self.today + timedelta(days=40),
           end_date=self.today + timedelta(days=40))

    def _states(self):
        return {n['title']: n['state'] for n in build_timeline()['nodes']}

    def test_states_are_assigned_correctly(self):
        s = self._states()
        self.assertEqual(s['گذشته'], 'past')
        self.assertEqual(s['در جریان'], 'now')
        self.assertEqual(s['بعدی'], 'next')
        self.assertEqual(s['دورتر'], 'future')

    def test_only_one_milestone_is_next(self):
        nodes = build_timeline()['nodes']
        self.assertEqual(sum(1 for n in nodes if n['state'] == 'next'), 1)

    def test_days_left_only_on_next(self):
        nodes = {n['title']: n for n in build_timeline()['nodes']}
        self.assertEqual(nodes['بعدی']['days_left'], 10)
        self.assertIsNone(nodes['گذشته']['days_left'])
        self.assertIsNone(nodes['در جریان']['days_left'])

    def test_empty_calendar_is_handled(self):
        AcademicCalendar.objects.all().delete()
        t = build_timeline()
        self.assertFalse(t['has_data'])
        self.assertEqual(t['nodes'], [])
        # صفحه اصلی نباید بشکند
        self.assertEqual(self.client.get(reverse('core:home')).status_code, 200)

    def test_timeline_renders_on_home(self):
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('class="acal"', body)
        self.assertIn('در جریان', body)
        self.assertIn('روز دیگر', body)

    def test_current_semester_is_chosen_over_others(self):
        """اگر چند سال تحصیلی باشد، سالی که امروز داخلش است انتخاب می‌شود."""
        AcademicCalendar.objects.create(
            title='سال قدیم', academic_year='1400-1401', semester='fall',
            start_date=self.today - timedelta(days=900),
            end_date=self.today - timedelta(days=800))
        t = build_timeline()
        self.assertEqual(t['academic_year'], self.year)
        self.assertNotIn('سال قدیم', [n['title'] for n in t['nodes']])


class TimelineClickTargetTests(TestCase):
    """هر مرحلهٔ تایم‌لاین به یک صفحهٔ واقعی پنل دانشجو لینک می‌شود."""

    def setUp(self):
        self.today = timezone.localdate()

    def _mk(self, **kw):
        base = dict(
            title='مرحله', academic_year='1405-1406', semester='fall',
            start_date=self.today, end_date=self.today,
        )
        base.update(kw)
        return AcademicCalendar.objects.create(**base)

    def test_action_resolves_to_real_url(self):
        item = self._mk(title='انتخاب واحد', action='registration')
        self.assertEqual(item.get_action_url(), reverse('dashboard:student_registration'))

    def test_every_action_choice_resolves(self):
        """هیچ گزینه‌ای در پنل نباید به آدرس شکسته منتهی شود."""
        broken = []
        for key, _label in AcademicCalendar.ACTION_CHOICES:
            if key in ('', 'external'):
                continue
            item = self._mk(title=f'x-{key}', action=key)
            if not item.get_action_url():
                broken.append(key)
        self.assertEqual(broken, [], f'این اقدام‌ها آدرس ندارند: {broken}')

    def test_external_url_is_used_when_selected(self):
        item = self._mk(action='external', external_url='https://example.org/x')
        self.assertEqual(item.get_action_url(), 'https://example.org/x')

    def test_no_action_means_no_link(self):
        self.assertEqual(self._mk(action='').get_action_url(), '')

    def test_icon_falls_back_to_action_default(self):
        self.assertEqual(self._mk(action='grades').display_icon, 'fa-award')
        self.assertEqual(self._mk(action='grades', icon='fa-star').display_icon, 'fa-star')

    def test_inactive_milestones_are_hidden(self):
        self._mk(title='پنهان', action='grades', is_active=False)
        self._mk(title='نمایان', action='grades', is_active=True)
        titles = [n['title'] for n in build_timeline()['nodes']]
        self.assertIn('نمایان', titles)
        self.assertNotIn('پنهان', titles)

    def test_order_overrides_date(self):
        self._mk(title='دوم', order=2, start_date=self.today,
                 end_date=self.today)
        self._mk(title='اول', order=1,
                 start_date=self.today + timedelta(days=5),
                 end_date=self.today + timedelta(days=5))
        titles = [n['title'] for n in build_timeline()['nodes']]
        self.assertEqual(titles[:2], ['اول', 'دوم'])

    def test_card_renders_as_link_on_home(self):
        self._mk(title='انتخاب واحد', action='registration',
                 start_date=self.today + timedelta(days=3),
                 end_date=self.today + timedelta(days=3))
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(reverse('dashboard:student_registration'), body)
        self.assertIn('acal-card', body)
        self.assertIn('acal-cap', body)   # نیم‌دایره


class HomeSectionTests(TestCase):
    """هر بخش صفحهٔ اصلی از پنل تصویر و عنوان می‌گیرد و پنهان‌شدنی است."""

    def test_home_renders_without_any_section_record(self):
        from core.models import HomeSection
        HomeSection.objects.all().delete()
        res = self.client.get(reverse('core:home'))
        self.assertEqual(res.status_code, 200)

    def test_every_seeded_form_file_exists_in_the_repo(self):
        """هر فرمی که دستور ثبت می‌کند باید فایل PDF همراهش باشد.

        فایل‌ها در core/seed_files/forms/ نگه داشته می‌شوند چون دیپلوی
        پوشهٔ media را دست نمی‌زند؛ اگر یکی جا بماند، لینک دانلود روی
        سایت ۴۰۴ می‌دهد بدون اینکه چیزی خطا بدهد.
        """
        import os
        from core.management.commands.seed_academic_forms import FORMS, SEED_DIR

        missing = [name for name, *_ in FORMS
                   if not os.path.isfile(os.path.join(SEED_DIR, name))]
        self.assertEqual(missing, [], 'فایل این فرم‌ها در مخزن نیست: %s' % missing)

    def test_no_mobile_display_errors(self):
        """بازرسی موبایل نباید خطای جدی پیدا کند.

        ایرادهای نمایش موبایل بی‌صدا هستند — نه لاگی می‌افتد نه تستی
        می‌شکند — تا وقتی کسی سایت را با گوشی باز کند. این تست همان
        بازرسی را بخشی از تست‌ها می‌کند.
        """
        import io
        from django.core.management import call_command

        buf = io.StringIO()
        call_command('check_responsive', stdout=buf)
        report = buf.getvalue()
        self.assertIn('0 خطا', report, report)

    def test_dark_banner_variables_win_over_light(self):
        """متغیرهای بنر در حالت تیره باید بر تعریف روشن غلبه کنند.

        تعریف روشن پایین‌تر در فایل است؛ اگر سلکتور تیره ویژگی برابر
        داشته باشد، ترتیب فایل برنده می‌شود و بنر در حالت تیره روشن
        می‌ماند — دقیقاً همان اشتباهی که یک بار رخ داد.
        """
        from pathlib import Path
        from django.conf import settings as dj

        css = (Path(dj.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(encoding='utf-8')
        dark = css.find(':root[data-theme="dark"] {')
        light = css.find('    --bnr-cream-050: #fffdf8;')
        self.assertGreater(dark, -1, 'بلوک تیرهٔ بنر با ویژگی کافی پیدا نشد')
        self.assertGreater(light, dark,
                           'تعریف روشن باید بعد از تیره باشد تا ویژگی معنا پیدا کند')

    def test_banner_content_is_unchanged(self):
        """بازطراحی بنر فقط ظاهری است؛ متن‌ها نباید عوض شده باشند."""
        body = self.client.get(reverse('core:home')).content.decode()
        for text in ('موسسه آموزش عالی علامه امینی',
                     'دانش · مهارت · آینده',
                     'وزارت علوم، تحقیقات و فناوری',
                     'Allameh Amini'):
            self.assertIn(text, body, 'از بنر افتاده: %s' % text)
        self.assertNotIn('علامه امینی بابلسر', body)

    def test_floating_buttons_do_not_overlap_on_mobile(self):
        """دکمهٔ «برو بالا» و دکمهٔ گفت‌وگو نباید روی هم بیفتند."""
        from pathlib import Path
        from django.conf import settings as dj

        css = (Path(dj.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(encoding='utf-8')
        mobile = css.split('@media (max-width: 576px)')[-1].split('}\n\n')[0]
        self.assertIn('.to-top', mobile, 'برای موبایل جای دکمهٔ بالا تعیین نشده')
        self.assertIn('.chatbot-btn', mobile)
        # هر دو گوشهٔ پایین‌اند؛ فاصلهٔ عمودی‌شان باید بیش از قطر دکمه باشد
        self.assertIn('inset-block-end: 84px', mobile)

    def test_live_search_covers_documents_and_persian_variants(self):
        """جستجو باید فرم‌ها را پیدا کند و «ي» عربی را هم بفهمد."""
        import io, json
        from django.core.management import call_command

        call_command('seed_academic_forms', verbosity=0, stdout=io.StringIO())

        res = self.client.get('/api/live-search/', {'q': 'معافیت'})
        titles = [r['title'] for r in json.loads(res.content)['results']]
        self.assertTrue(any('معافیت' in t for t in titles), titles)

        # همان عبارت با «ي» عربی و بدون نیم‌فاصله باید همان را بیاورد
        res = self.client.get('/api/live-search/', {'q': 'پايان'})
        titles = [r['title'] for r in json.loads(res.content)['results']]
        self.assertTrue(titles, 'شکل عربی حروف نتیجه‌ای نداد')

    def test_live_search_is_rate_limited(self):
        """اندپوینت عمومی بدون سقف، راه ساده‌ای برای فشار به دیتابیس است."""
        from django.core.cache import cache
        cache.clear()
        last = None
        for _ in range(95):
            last = self.client.get('/api/live-search/', {'q': 'الف'})
        self.assertEqual(last.status_code, 429)
        cache.clear()

    def test_documents_page_filters_by_section(self):
        """فیلتر «آموزش / پژوهش» باید واقعاً فهرست را جدا کند."""
        import io
        from django.core.management import call_command
        from core.models import DownloadableDocument

        call_command('seed_academic_forms', verbosity=0, stdout=io.StringIO())
        url = reverse('core:documents')

        research = self.client.get(url, {'degree': 'master', 'section': 'research'})
        body = research.content.decode()
        self.assertIn('پروپوزال', body)
        self.assertNotIn('برگه حذف و اضافه واحد', body)

        academic = self.client.get(url, {'degree': 'master', 'section': 'academic'})
        body = academic.content.decode()
        self.assertNotIn('پروپوزال', body)

        # بخش نامعتبر نباید صفحه را بشکند یا همه‌چیز را پنهان کند
        bogus = self.client.get(url, {'section': 'nope'})
        self.assertEqual(bogus.status_code, 200)

        self.assertEqual(
            DownloadableDocument.objects.filter(section='research').count(), 8)

    def test_seeding_forms_is_idempotent(self):
        from django.core.management import call_command
        from core.models import DownloadableDocument

        import io
        call_command('seed_academic_forms', verbosity=0, stdout=io.StringIO())
        first = DownloadableDocument.objects.count()
        call_command('seed_academic_forms', verbosity=0, stdout=io.StringIO())
        self.assertEqual(DownloadableDocument.objects.count(), first,
                         'اجرای دوباره نباید رکورد تکراری بسازد')

    def test_no_multiline_django_comments_in_templates(self):
        """کامنت {# … #} در جنگو فقط تک‌خطی است.

        اگر چندخطی نوشته شود، جنگو آن را کامنت نمی‌شناسد و **متنش را روی
        صفحه چاپ می‌کند**. یک‌بار این اتفاق در تایم‌لاین و در صفحهٔ پیگیری
        پذیرش افتاد و متن توضیحی به کاربر نمایش داده شد.
        """
        from pathlib import Path
        from django.conf import settings as dj_settings

        offenders = []
        for base in dj_settings.TEMPLATES[0]['DIRS']:
            for path in Path(base).rglob('*.html'):
                for no, line in enumerate(
                        path.read_text(encoding='utf-8').splitlines(), start=1):
                    if '{#' in line and '#}' not in line:
                        offenders.append('%s:%d' % (path.name, no))

        self.assertEqual(
            offenders, [],
            'کامنت چندخطی {# … #} روی صفحه چاپ می‌شود؛ از {%% comment %%} '
            'استفاده کنید: %s' % offenders,
        )

    def test_every_section_choice_is_wired_into_the_page(self):
        """هر کلیدی که در پنل انتخاب‌شدنی است باید در قالب هم استفاده شود.

        وگرنه ادمین برای بخشی تصویر آپلود می‌کند و هیچ اتفاقی نمی‌افتد.
        """
        from pathlib import Path
        from django.conf import settings as dj_settings
        from core.models import HomeSection

        templates = ''
        for base in dj_settings.TEMPLATES[0]['DIRS']:
            for name in ('core/home.html', 'core/_academic_timeline.html'):
                path = Path(base) / name
                if path.exists():
                    templates += path.read_text(encoding='utf-8')

        missing = [key for key, _ in HomeSection.SECTION_CHOICES
                   if 'sections.%s' % key not in templates]
        self.assertEqual(missing, [], 'این بخش‌ها در قالب وصل نشده‌اند: %s' % missing)

    def test_hiding_the_stats_bar_removes_it(self):
        from core.models import HomeSection
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('دانشجوی فعال', body)
        HomeSection.objects.update_or_create(
            key='stats', defaults={'is_visible': False})
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('دانشجوی فعال', body)

    def test_cta_title_comes_from_the_panel(self):
        from core.models import HomeSection
        HomeSection.objects.update_or_create(
            key='cta', defaults={'title': 'همین حالا اقدام کنید', 'is_visible': True})
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('همین حالا اقدام کنید', body)
        self.assertNotIn('آماده‌اید دانشجوی ما شوید؟', body)

    def test_dark_overlay_flag_needs_both_image_and_overlay(self):
        from core.models import HomeSection
        sec = HomeSection(key='news', overlay='dark')
        self.assertFalse(sec.is_dark_overlay, 'بدون تصویر نباید متن سفید شود')
        sec.image = 'home/bg.jpg'
        self.assertTrue(sec.is_dark_overlay)
        sec.overlay = 'light'
        self.assertFalse(sec.is_dark_overlay)

    def test_custom_title_replaces_default(self):
        from core.models import HomeSection
        HomeSection.objects.update_or_create(
            key='features', defaults={'title': 'چرا اینجا؟', 'is_visible': True})
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('چرا اینجا؟', body)

    def test_hiding_a_section_removes_it(self):
        from core.models import HomeFeature, HomeSection
        HomeFeature.objects.create(title='مزیت آزمایشی', icon='fa-star')
        HomeSection.objects.update_or_create(
            key='features', defaults={'is_visible': True})
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('مزیت آزمایشی', body)

        HomeSection.objects.filter(key='features').update(is_visible=False)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('مزیت آزمایشی', body)

    def test_features_come_from_database(self):
        from core.models import HomeFeature
        HomeFeature.objects.all().delete()
        feature = HomeFeature.objects.create(title='مزیت یکتا', description='توضیح',
                                             icon='fa-flask', tone='green', order=1)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('مزیت یکتا', body)
        self.assertIn('fa-flask', body)
        # رنگ از مدل می‌آید نه از قالب — هگز را از خود مدل بخوان تا تست با
        # هر بار عوض‌شدن پالت نشکند
        self.assertIn(feature.color, body)

    def test_inactive_feature_is_hidden(self):
        from core.models import HomeFeature
        HomeFeature.objects.create(title='غیرفعال', icon='fa-star', is_active=False)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('غیرفعال', body)


class LeadershipSectionTests(TestCase):
    """درباره موسسه / حوزه ریاست / معاونت‌ها — ساختار و کامل بودن."""

    def test_deputies_page_redirects_instead_of_showing_nothing(self):
        """«معاونین» و «معاونت‌ها» یک مفهوم بودند و اولی همیشه خالی بود."""
        res = self.client.get(reverse('core:deputies'))
        self.assertEqual(res.status_code, 301)
        self.assertIn(reverse('core:vices_list'), res['Location'])

    def test_presidency_lists_vices_from_the_model_that_has_data(self):
        from core.models import VicePresidency

        VicePresidency.objects.update_or_create(
            vice_type='education',
            defaults={'full_name': 'دکتر آزمایشی', 'is_active': True},
        )
        body = self.client.get(reverse('core:presidency')).content.decode()
        self.assertIn('دکتر آزمایشی', body)

    def test_presidency_office_is_a_real_singleton(self):
        """رکورد دوم روی سایت دیده نمی‌شود، پس ساختنش باید بسته باشد."""
        from django.contrib.admin.sites import site
        from core.models import PresidencyOffice

        PresidencyOffice.objects.get_or_create(pk=1)
        model_admin = site._registry[PresidencyOffice]

        class _Req:
            pass

        self.assertFalse(model_admin.has_add_permission(_Req()))
        self.assertFalse(model_admin.has_delete_permission(_Req()))

    def test_completeness_flags_missing_critical_fields(self):
        from core.completeness import evaluate
        from core.models import VicePresidency

        vice = VicePresidency(vice_type='research', full_name='')
        data = evaluate(vice)
        self.assertLess(data['percent'], 30)
        self.assertIn('نام معاون', data['critical'])

        vice.full_name = 'دکتر نمونه'
        vice.description = 'معرفی'
        vice.duties = 'وظایف'
        better = evaluate(vice)
        self.assertGreater(better['percent'], data['percent'])
        self.assertNotIn('نام معاون', better['critical'])

    def test_completeness_profiles_reference_real_fields(self):
        """اگر فیلدی در مدل تغییر نام دهد، سنجه باید بشکند نه اینکه
        بی‌صدا آن را «خالی» بشمارد و درصد را غلط بدهد."""
        from django.apps import apps
        from core.completeness import PROFILES

        for label, spec in PROFILES.items():
            model = apps.get_model(label)
            names = {f.name for f in model._meta.get_fields()
                     if hasattr(f, 'attname')}
            unknown = [row[0] for row in spec if row[0] not in names]
            self.assertEqual(unknown, [], '%s → %s' % (label, unknown))


class PresidencyUnitTests(TestCase):
    """واحدهای دفتر ریاست — مسئول، تماس و شرح وظایف."""

    def setUp(self):
        import io
        from django.core.management import call_command
        call_command('seed_presidency', verbosity=0, stdout=io.StringIO())

    def test_units_carry_contact_details(self):
        from core.models import PresidencyOfficeUnit

        unit = PresidencyOfficeUnit.objects.get(slug='modir-daftar')
        self.assertTrue(unit.duty_list, 'شرح وظایف خالی است')
        self.assertGreaterEqual(len(unit.duty_list), 3)
        self.assertIn('داخلی', unit.contact_line)
        self.assertTrue(unit.location)

    def test_unit_page_shows_duties_and_contact(self):
        res = self.client.get(
            reverse('core:presidency_office_unit', args=['modir-daftar']))
        body = res.content.decode()
        self.assertEqual(res.status_code, 200)
        self.assertIn('شرح وظایف', body)
        self.assertIn('ساختمان مرکزی', body)

    def test_president_message_reaches_the_page(self):
        body = self.client.get(reverse('core:presidency')).content.decode()
        self.assertIn('خانهٔ اندیشه', body)

    def test_seed_does_not_overwrite_admin_edits(self):
        import io
        from django.core.management import call_command
        from core.models import PresidencyOfficeUnit

        unit = PresidencyOfficeUnit.objects.get(slug='modir-daftar')
        unit.manager_name = 'دکتر واقعی'
        unit.save()

        call_command('seed_presidency', verbosity=0, stdout=io.StringIO())
        unit.refresh_from_db()
        self.assertEqual(unit.manager_name, 'دکتر واقعی')

    def test_duty_list_ignores_blank_and_bullet_prefixes(self):
        from core.models import PresidencyOfficeUnit

        unit = PresidencyOfficeUnit(duties='- اول\n\n• دوم\n   \nسوم')
        self.assertEqual(unit.duty_list, ['اول', 'دوم', 'سوم'])


class NoFabricatedContentTests(TestCase):
    """صفحهٔ اصلی نباید داده‌ای بسازد که وجود ندارد."""

    FABRICATED = ('دکتر محمد احمدی', 'دانشکده مهندسی')

    def test_home_shows_no_invented_people_or_faculties(self):
        """پیش از این، نبودِ داده با کارت‌های ساختگی پر می‌شد.

        روی سایت یک موسسهٔ واقعی این از خالی بودن بدتر است: چهار استاد
        هم‌نام و شش دانشکدهٔ یکسان، برای بازدیدکننده واقعی به نظر می‌رسند.
        """
        from faculty.models import Professor
        from academics.models import Department

        Professor.objects.all().delete()
        Department.objects.all().delete()

        body = self.client.get(reverse('core:home')).content.decode()
        for text in self.FABRICATED:
            self.assertNotIn(text, body, 'محتوای ساختگی روی صفحه: %s' % text)

    def test_empty_state_is_only_visible_to_staff(self):
        from django.contrib.auth.models import User
        from faculty.models import Professor

        Professor.objects.all().delete()

        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('افزودن از پنل ادمین', body)

        User.objects.create_user('kar', password='Str0ng!Pass2026', is_staff=True)
        self.client.login(username='kar', password='Str0ng!Pass2026')
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('افزودن از پنل ادمین', body)

    def test_featured_flag_controls_the_home_section(self):
        from faculty.models import Professor

        Professor.objects.all().delete()
        Professor.objects.create(first_name='الف', last_name='یکم',
                                 rank='assistant', is_active=True, order=1)
        starred = Professor.objects.create(
            first_name='ب', last_name='دوم', rank='assistant',
            is_active=True, is_featured=True, order=9)

        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(starred.get_full_name(), body)
        # وقتی کسی علامت خورده، ترتیب دیگر تعیین‌کننده نیست
        self.assertNotIn('الف یکم', body)

    def test_falls_back_to_order_when_nobody_is_featured(self):
        from faculty.models import Professor

        Professor.objects.all().delete()
        prof = Professor.objects.create(first_name='ج', last_name='سوم',
                                        rank='assistant', is_active=True)
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(prof.get_full_name(), body)


class JalaliYearDisplayTests(TestCase):
    """سال تحصیلی میلادی ذخیره می‌شود ولی باید شمسی دیده شود."""

    def test_tuition_display_converts_the_year(self):
        from academics.models import Department, Major
        from admissions.models import TuitionStructure

        dep = Department.objects.create(name='آزمایشی', slug='azmayeshi')
        major = Major.objects.create(name='رشتهٔ آزمایشی', slug='reshte-x',
                                     department=dep, degree='bachelor_continuous')
        TuitionStructure.objects.create(
            major=major, academic_year='2026-2027',
            fixed_fee=5000000, is_active=True)

        shown = major.tuition_display
        self.assertIn('۱۴۰۵-۱۴۰۶', shown, shown)
        self.assertNotIn('2026', shown)
        self.assertNotIn('5,000,000', shown)   # رقم هم فارسی شود
        self.assertIn('۵٬۰۰۰٬۰۰۰'.replace('٬', ','), shown)

    def test_year_range_helper_leaves_jalali_untouched(self):
        from core.jalali import jalali_year_range

        self.assertEqual(jalali_year_range('1405-1406'), '۱۴۰۵-۱۴۰۶')
        self.assertEqual(jalali_year_range('2026-2027'), '۱۴۰۵-۱۴۰۶')
        self.assertEqual(jalali_year_range(''), '')

    def test_no_template_prints_a_raw_academic_year(self):
        """هر جای قالب که academic_year چاپ می‌شود باید فیلتر شمسی بخورد."""
        import re
        from pathlib import Path
        from django.conf import settings as dj

        offenders = []
        for base in dj.TEMPLATES[0]['DIRS']:
            for path in Path(base).rglob('*.html'):
                for no, line in enumerate(
                        path.read_text(encoding='utf-8').splitlines(), 1):
                    for m in re.finditer(r'\{\{[^}]*academic_year[^}]*\}\}', line):
                        chunk = m.group(0)
                        if 'jalali' not in chunk and 'semester_jalali' not in chunk:
                            offenders.append('%s:%d' % (path.name, no))
        self.assertEqual(offenders, [],
                         'سال تحصیلی بدون تبدیل شمسی: %s' % offenders)


class VicesNavigationTests(TestCase):
    """«معاونت ها» از نوار بالا حذف و با «حوزه ریاست» ادغام شد."""

    def setUp(self):
        from core.models import VicePresidency
        from django.core.cache import cache

        cache.clear()
        VicePresidency.objects.all().delete()
        self.vice = VicePresidency.objects.create(
            vice_type='education', full_name='دکتر نمونه',
            academic_rank='دانشیار', description='معرفی معاونت آموزشی',
            is_active=True)

    def test_navbar_has_no_separate_vices_menu(self):
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn('fa-sitemap" style="font-size:13px;margin-left:3px;"></i> معاونت ها', body)

    def test_vices_appear_inside_the_presidency_menu(self):
        body = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('حوزه ریاست', body)
        self.assertIn('همهٔ معاونین و معاونت‌ها', body)
        self.assertIn(self.vice.get_vice_type_display(), body)

    def test_menu_follows_the_database(self):
        """معاونت غیرفعال باید از منو برود، بدون دست‌زدن به قالب."""
        from django.core.cache import cache

        self.vice.is_active = False
        self.vice.save()
        cache.clear()

        body = self.client.get(reverse('core:home')).content.decode()
        self.assertNotIn(
            reverse('core:vice_detail', args=[self.vice.vice_type]), body)

    def test_list_page_shows_the_person_not_a_fixed_card(self):
        body = self.client.get(reverse('core:vices_list')).content.decode()
        self.assertIn('دکتر نمونه', body)
        self.assertIn('دانشیار', body)

    def test_unregistered_vices_are_reported_to_staff_only(self):
        from django.contrib.auth.models import User

        body = self.client.get(reverse('core:vices_list')).content.decode()
        self.assertNotIn('هنوز رکوردی ندارند', body)

        User.objects.create_user('kar2', password='Str0ng!Pass2026', is_staff=True)
        self.client.login(username='kar2', password='Str0ng!Pass2026')
        body = self.client.get(reverse('core:vices_list')).content.decode()
        self.assertIn('هنوز رکوردی ندارند', body)
        self.assertIn('معاونت پژوهشی و فناوری', body)


class CompletenessPlaceholderTests(TestCase):
    """جای‌نگهدار نباید «پر» شمرده شود."""

    def test_placeholder_counts_as_missing(self):
        from core.completeness import evaluate
        from core.models import PresidencyOffice

        office = PresidencyOffice(
            president_name='[نام را از پنل ادمین وارد کنید]',
            president_title='دانشیار',
            president_message='پیام',
        )
        data = evaluate(office)
        self.assertIn('نام رئیس', data['critical'],
                      'جای‌نگهدار به‌عنوان مقدار واقعی شمرده شد')

        office.president_name = 'دکتر واقعی'
        self.assertNotIn('نام رئیس', evaluate(office)['critical'])

    def test_ordinary_brackets_inside_text_are_not_placeholders(self):
        from core.completeness import _is_placeholder

        self.assertTrue(_is_placeholder('[نام]'))
        self.assertFalse(_is_placeholder('دکتر [الف] احمدی'))
        self.assertFalse(_is_placeholder('دانشیار'))


class SMSQueueTests(TestCase):
    """پیامک نباید داخل مسیر درخواست کاربر فرستاده شود."""

    def test_queue_off_sends_immediately(self):
        from django.test import override_settings
        from core.sms_queue import QueuedSMS, queue_enabled

        with override_settings(SMS_QUEUE=False):
            self.assertFalse(queue_enabled())
        self.assertEqual(QueuedSMS.objects.count(), 0)

    def test_queue_on_stores_instead_of_sending(self):
        from django.test import override_settings
        from core.notify import notify_phone
        from core.sms_queue import QueuedSMS

        with override_settings(SMS_QUEUE=True, SMS_ENABLED=False):
            ok = notify_phone('09121234567', 'پیام آزمایشی')

        self.assertTrue(ok)
        row = QueuedSMS.objects.get()
        self.assertEqual(row.status, 'pending')
        self.assertIn('آزمایشی', row.message)

    def test_flush_marks_failed_after_max_attempts(self):
        """پیامی که مدام شکست بخورد باید بعد از چند تلاش رها شود.

        با SMS_ENABLED=False ارسال «موفق» شمرده می‌شود (حالت توسعه)،
        پس برای دیدن مسیر شکست باید خود فرستنده را ناموفق کرد.
        """
        from unittest.mock import patch
        from core.sms_queue import MAX_ATTEMPTS, QueuedSMS, flush

        QueuedSMS.objects.create(phone='09121234567', message='x')
        with patch('core.sms.send_sms', return_value=False):
            for _ in range(MAX_ATTEMPTS):
                flush()

        row = QueuedSMS.objects.get()
        self.assertEqual(row.status, 'failed')
        self.assertEqual(row.attempts, MAX_ATTEMPTS)

    def test_successful_send_marks_the_row(self):
        from unittest.mock import patch
        from core.sms_queue import QueuedSMS, flush

        QueuedSMS.objects.create(phone='09121234567', message='x')
        with patch('core.sms.send_sms', return_value=True):
            result = flush()

        row = QueuedSMS.objects.get()
        self.assertEqual(row.status, 'sent')
        self.assertIsNotNone(row.sent_at)
        self.assertEqual(result['sent'], 1)

    def test_invalid_phone_is_not_queued(self):
        from django.test import override_settings
        from core.notify import notify_phone
        from core.sms_queue import QueuedSMS

        with override_settings(SMS_QUEUE=True):
            self.assertFalse(notify_phone('123', 'کوتاه'))
        self.assertEqual(QueuedSMS.objects.count(), 0)


class TrackingCodeTests(TestCase):
    """کد رهگیری باید زیر فشار هم‌زمان هم یکتا بماند."""

    @classmethod
    def setUpTestData(cls):
        from academics.models import Department, Major

        dep = Department.objects.create(name='آزمون', slug='azmoon-tc')
        cls.major = Major.objects.create(
            name='رشتهٔ آزمون', slug='reshte-tc',
            department=dep, degree='bachelor_continuous')

    def _make(self, index):
        from admissions.models import Application

        return Application.objects.create(
            first_name='الف', last_name='ب%d' % index,
            national_id='', phone='0912000%04d' % index,
            degree='bachelor_continuous', desired_major=self.major,
        )

    def test_codes_are_unique_across_many_saves(self):
        codes = {self._make(i).tracking_code for i in range(30)}
        self.assertEqual(len(codes), 30)
        self.assertTrue(all(len(c) == 12 for c in codes))

    def test_a_taken_code_is_retried_not_raised(self):
        """اگر کد تصادفی تکراری دربیاید، باید دوباره تولید شود نه ۵۰۰."""
        from unittest.mock import patch
        from admissions.models import Application

        first = self._make(100)
        taken = first.tracking_code
        fresh = '%012d' % 123456789012

        # اولین تلاش کد گرفته‌شده را برمی‌گرداند، دومی کد آزاد
        with patch.object(Application, '_gen_tracking',
                          side_effect=[taken, fresh]):
            second = self._make(101)

        self.assertEqual(second.tracking_code, fresh)
        self.assertEqual(Application.objects.filter(tracking_code=taken).count(), 1)

    def test_existing_code_is_not_regenerated(self):
        app = self._make(200)
        original = app.tracking_code
        app.first_name = 'تغییر'
        app.save()
        app.refresh_from_db()
        self.assertEqual(app.tracking_code, original)


class AdminImageUploadTests(TestCase):
    """آپلود عکس در پنل ادمین — مسیری که تا حالا هیچ تستی نداشت.

    این تست‌ها خطای ۵۰۰ سرور را بازتولید *نمی‌کنند*: با MEDIA_ROOT
    ناموجود هم پاس می‌شوند، چون FileSystemStorage خودش پوشه‌های
    میانی را می‌سازد. پس علت واقعی روی سرور نبودِ پوشه نیست، بلکه
    نداشتن مجوز نوشتن در آن است — چیزی که فقط از logs/django.log
    یا خروجی diagnose.py معلوم می‌شود.

    ارزش این تست‌ها جای دیگری است: مسیر «فرم را با یک فایل تصویری
    بفرست و مطمئن شو ذخیره شد» تا امروز اصلاً پوشش نداشت، و صفحهٔ
    ویرایشی که رکوردش به فایل گم‌شده اشاره می‌کند هم همین‌طور.
    """

    @classmethod
    def setUpClass(cls):
        cls._media = os.path.join(
            tempfile.mkdtemp(prefix='upload-test-'), 'never', 'created')
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(os.path.dirname(os.path.dirname(cls._media)),
                      ignore_errors=True)

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'uploader', 'u@example.com', 'pw-for-test-only')
        self.client.force_login(self.staff)

    def _png(self, name='photo.png'):
        """کوچک‌ترین PNG معتبر — Pillow باید بتواند بازش کند."""
        data = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8'
            b'z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
        return SimpleUploadedFile(name, data, content_type='image/png')

    def test_presidency_photo_upload_saves(self):
        office = PresidencyOffice.objects.create(president_name='رئیس')
        res = self.client.post(
            reverse('admin:core_presidencyoffice_change', args=[office.pk]),
            {
                'president_name': 'دکتر حسن فارسیجانی',
                'president_title': '', 'president_bio': '',
                'president_education': '', 'president_resume': '',
                'president_email': '', 'president_phone': '',
                'president_message': '', 'office_manager_name': '',
                'office_duties': '', 'office_address': '',
                'office_phone': '', 'office_fax': '', 'office_email': '',
                'office_hours': '',
                'president_photo': self._png(),
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        office.refresh_from_db()
        self.assertTrue(office.president_photo, 'عکس ذخیره نشد')

    def test_security_office_photo_upload_saves(self):
        office = SecurityOffice.objects.create(manager_name='مسئول')
        form = {f: '' for f in (
            'manager_name', 'manager_title', 'description', 'duties',
            'phone', 'emergency_phone', 'email', 'location', 'office_hours',
        ) if hasattr(office, f)}
        form['manager_name'] = 'عباس اسدی امیری'
        if hasattr(office, 'manager_photo'):
            form['manager_photo'] = self._png('sec.png')

        res = self.client.post(
            reverse('admin:core_securityoffice_change', args=[office.pk]),
            form, follow=True)
        self.assertEqual(res.status_code, 200)

    def test_change_pages_with_an_image_field_open(self):
        """صفحهٔ ویرایش نباید ۵۰۰ بدهد، حتی وقتی فایل عکس گم شده باشد."""
        office = PresidencyOffice.objects.create(
            president_name='رئیس', president_photo='presidency/gone.jpg')
        res = self.client.get(
            reverse('admin:core_presidencyoffice_change', args=[office.pk]))
        self.assertEqual(res.status_code, 200)
