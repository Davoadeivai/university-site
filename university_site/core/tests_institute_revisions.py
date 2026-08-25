"""بندهای سند «اصلاحات سایت دانشگاه علامه امینی».

هر تست به شمارهٔ بند سند اشاره دارد تا اگر روزی چیزی برگشت، معلوم
باشد کدام خواستهٔ موسسه نقض شده است.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings, VicePresidency


class HeaderRevisionTests(TestCase):
    """بندهای ۳، ۴ و ۵ — سربرگ."""

    def _home(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_slogan_removed(self):
        """بند ۴: شعار «دانش، مهارت، آینده» حذف شود."""
        self.assertNotIn('دانش · مهارت · آینده', self._home())

    def test_name_uses_arial(self):
        """بند ۳: نام موسسه با فونت Arial و درشت‌تر."""
        from pathlib import Path
        from django.conf import settings as dj
        css = (Path(dj.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
            encoding='utf-8')
        start = css.index(chr(10) + '.bnr-fa {')
        block = css[start:css.index('}', start)]
        self.assertIn('font-family: Arial', block)
        # اندازهٔ بیشینه باید از نسخهٔ قبلی (1.9rem) بزرگ‌تر باشد
        self.assertIn('2.45rem', block)

    def test_world_class_logo_on_both_sides(self):
        """بند ۵: لوگوی کلاس جهانی در دو سوی عنوان."""
        SiteSettings.objects.all().delete()
        SiteSettings.objects.create(world_class_logo='site/wcu.png')
        banner = self._home().split('bnr-name')[1].split('bnr-state')[0]
        self.assertEqual(banner.count('bnr-wcu'), 2)


class NavigationRevisionTests(TestCase):
    """بندهای ۱۱، ۱۳، ۱۴ و ۱۶ — منوی اصلی."""

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_faculty_replaces_members(self):
        """بند ۱۱: «اعضای موسسه» به «هیئت علمی» تغییر کند."""
        nav = self._nav()
        self.assertIn('هیئت علمی', nav)
        self.assertNotIn('اعضای موسسه', nav)

    def test_boards_are_out_of_the_menu(self):
        """بند ۱۱: هیئت امنا و هیئت موسس از منو حذف شوند."""
        nav = self._nav()
        self.assertNotIn('هیات موسس دانشگاه', nav)
        self.assertNotIn('هیات امناء دانشگاه', nav)

    def test_board_pages_still_exist(self):
        """حذف از منو یعنی حذف از منو، نه حذف صفحه."""
        for name in ('core:board_founders', 'core:board_trustees'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_deputies_have_their_own_menu_in_order(self):
        """بند ۱۳: معاونین در منوی اصلی، با ترتیب خواسته‌شده."""
        nav = self._nav()
        order = ['۱. معاونت آموزشی', '۲. معاونت پژوهشی',
                 '۳. معاونت اداری و مالی', '۴. معاونت دانشجویی',
                 '۵. معاونت فنی و عمرانی']
        positions = []
        for label in order:
            self.assertIn(label, nav, 'در منو نیست: %s' % label)
            positions.append(nav.index(label))
        self.assertEqual(positions, sorted(positions), 'ترتیب معاونت‌ها به هم خورده')

    def test_graduate_studies_moved_under_education(self):
        """بند ۱۶: تحصیلات تکمیلی از منوهای اصلی به زیر معاونت آموزشی."""
        nav = self._nav()
        # دیگر یک منوی سطح‌بالا نیست
        self.assertNotIn('fa-graduation-cap" style="font-size:13px;'
                         'margin-left:3px;"></i> تحصیلات تکمیلی', nav)
        # ولی زیر معاونت آموزشی هست
        block = nav.split('۱. معاونت آموزشی')[1].split('۲. معاونت پژوهشی')[0]
        self.assertIn('تحصیلات تکمیلی', block)

    def test_international_office_moved_under_research(self):
        """بند ۱۴: دفتر همکاری‌های علمی زیر معاونت پژوهشی."""
        nav = self._nav()
        block = nav.split('۲. معاونت پژوهشی')[1].split('۳. معاونت اداری')[0]
        self.assertIn('دفتر همکاری‌های علمی', block)
        # و دیگر زیر «حوزه ریاست» نیست
        presidency = nav.split('حوزه ریاست')[1].split('معاونین')[0]
        self.assertNotIn('دفتر همکاری', presidency)


class DoctorPrefixTests(TestCase):
    """بند ۱۸: «دکتر» پیش از نام معاونان و مدیران گروه."""

    def test_a_bare_name_gets_the_prefix(self):
        VicePresidency.objects.create(
            vice_type='education', full_name='علی رضایی')
        call_command('prefix_doctor_titles', stdout=StringIO())
        self.assertEqual(
            VicePresidency.objects.first().full_name, 'دکتر علی رضایی')

    def test_an_existing_title_is_left_alone(self):
        """«دکتر دکتر» بدتر از نبودنش است."""
        VicePresidency.objects.create(
            vice_type='research', full_name='دکتر مریم احمدی')
        call_command('prefix_doctor_titles', stdout=StringIO())
        self.assertEqual(
            VicePresidency.objects.first().full_name, 'دکتر مریم احمدی')

    def test_other_honorifics_are_respected(self):
        VicePresidency.objects.create(
            vice_type='student', full_name='مهندس حسن کریمی')
        call_command('prefix_doctor_titles', stdout=StringIO())
        self.assertEqual(
            VicePresidency.objects.first().full_name, 'مهندس حسن کریمی')

    def test_group_heads_are_covered(self):
        from academics.models import AcademicGroup, Department
        AcademicGroup.objects.create(
            name='گروه صنعتی', slug='sanati', head='زهرا موسوی',
            department=Department.objects.create(name='مدیریت', slug='modiriat'))
        call_command('prefix_doctor_titles', stdout=StringIO())
        self.assertEqual(
            AcademicGroup.objects.first().head, 'دکتر زهرا موسوی')

    def test_dry_run_changes_nothing(self):
        VicePresidency.objects.create(
            vice_type='education', full_name='علی رضایی')
        call_command('prefix_doctor_titles', '--dry-run', stdout=StringIO())
        self.assertEqual(VicePresidency.objects.first().full_name, 'علی رضایی')

    def test_running_twice_is_safe(self):
        VicePresidency.objects.create(
            vice_type='education', full_name='علی رضایی')
        call_command('prefix_doctor_titles', stdout=StringIO())
        call_command('prefix_doctor_titles', stdout=StringIO())
        self.assertEqual(
            VicePresidency.objects.first().full_name, 'دکتر علی رضایی')


class GroupCardRevisionTests(TestCase):
    """بند ۱۲: عکس و نام مدیر گروه در فهرست گروه‌های آموزشی."""

    def test_the_card_shows_the_head_with_a_photo_slot(self):
        from academics.models import AcademicGroup, Department
        AcademicGroup.objects.create(
            name='گروه بازرگانی', slug='bazargani', head='دکتر زهرا موسوی',
            department=Department.objects.create(name='مدیریت', slug='modiriat'))
        html = self.client.get(
            reverse('academics:groups_list')).content.decode()
        self.assertIn('grp-head', html)
        self.assertIn('دکتر زهرا موسوی', html)
        # بدون عکس هم نباید تصویر شکسته بیاید
        self.assertIn('grp-head-empty', html)


class GraduateGroupsTests(TestCase):
    """بند ۱۷: چهار گروه دارای تحصیلات تکمیلی، با ترتیب سند."""

    def _group(self, name, slug):
        from academics.models import AcademicGroup, Department
        dep, _ = Department.objects.get_or_create(
            name='مدیریت', defaults={'slug': 'modiriat'})
        return AcademicGroup.objects.create(
            name=name, slug=slug, department=dep)

    def test_the_four_named_groups_are_marked(self):
        from academics.models import AcademicGroup
        self._group('گروه آموزشی بازرگانی', 'bazargani')
        self._group('گروه آموزشی صنعتی', 'sanati')
        self._group('گروه آموزش علوم تربیتی', 'tarbiati')
        self._group('گروه آموزشی حسابداری', 'hesabdari')

        call_command('set_graduate_groups', stdout=StringIO())

        marked = list(AcademicGroup.objects
                      .filter(has_graduate=True)
                      .order_by('graduate_order')
                      .values_list('name', flat=True))
        self.assertEqual(marked, [
            'گروه آموزشی بازرگانی',
            'گروه آموزشی صنعتی',
            'گروه آموزش علوم تربیتی',
            'گروه آموزشی حسابداری',
        ])

    def test_a_bare_name_matches_too(self):
        """نام گروه در پنل ممکن است «حسابداری» تنها باشد."""
        from academics.models import AcademicGroup
        self._group('حسابداری', 'hesabdari')
        call_command('set_graduate_groups', stdout=StringIO())
        self.assertTrue(AcademicGroup.objects.first().has_graduate)

    def test_arabic_letters_do_not_break_the_match(self):
        from academics.models import AcademicGroup
        self._group('گروه آموزشي بازرگاني', 'bazargani')
        call_command('set_graduate_groups', stdout=StringIO())
        self.assertTrue(AcademicGroup.objects.first().has_graduate)

    def test_a_group_outside_the_list_is_unmarked(self):
        """اگر گروهی پیش‌تر علامت خورده و در سند نیست، برداشته شود."""
        from academics.models import AcademicGroup
        other = self._group('گروه آموزشی معماری', 'memari')
        other.has_graduate = True
        other.save(update_fields=['has_graduate'])

        call_command('set_graduate_groups', stdout=StringIO())
        other.refresh_from_db()
        self.assertFalse(other.has_graduate)

    def test_a_missing_group_is_reported_not_silent(self):
        out = StringIO()
        self._group('گروه آموزشی بازرگانی', 'bazargani')
        call_command('set_graduate_groups', stdout=out)
        self.assertIn('پیدا نشد', out.getvalue())
        self.assertIn('حسابداری', out.getvalue())

    def test_running_twice_is_safe(self):
        from academics.models import AcademicGroup
        self._group('گروه آموزشی صنعتی', 'sanati')
        call_command('set_graduate_groups', stdout=StringIO())
        call_command('set_graduate_groups', stdout=StringIO())
        group = AcademicGroup.objects.first()
        self.assertTrue(group.has_graduate)
        self.assertEqual(group.graduate_order, 2)

    def test_they_appear_under_the_education_deputy(self):
        from django.core.cache import cache
        self._group('گروه آموزشی حسابداری', 'hesabdari')
        call_command('set_graduate_groups', stdout=StringIO())
        cache.clear()

        html = self.client.get(reverse('core:home')).content.decode()
        nav = html.split('id="mainNav"')[1].split('</nav>')[0]
        block = nav.split('۱. معاونت آموزشی')[1].split('۲. معاونت پژوهشی')[0]
        self.assertIn('گروه آموزشی حسابداری', block)


class UploadedLogoCannotStretchTheLayoutTests(TestCase):
    """هر تصویری که ادمین آپلود کند باید در قاب خودش بماند.

    نشان کلاس جهانی که موسسه فرستاد یک اسکرین‌شات ۵۹۱×۱۲۸۰ بود، نه
    لوگوی مربع. با بستنِ فقط عرض، ارتفاعش در سربرگ به ۱۳۹ پیکسل
    می‌رسید، نوار کش می‌آمد و نام موسسه از قاب بیرون می‌رفت — بدون
    هیچ خطایی، فقط یک صفحهٔ به‌هم‌ریخته.
    """

    def _rule(self, selector):
        from pathlib import Path
        from django.conf import settings
        css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
            encoding='utf-8')
        start = css.index(chr(10) + selector + ' {') + 1
        return css[start:css.index('}', start)]

    def test_the_header_emblem_is_boxed_in_both_directions(self):
        rule = self._rule('.bnr-wcu')
        self.assertIn('inline-size', rule)
        self.assertIn('block-size', rule)
        self.assertNotIn('block-size: auto', rule,
                         'ارتفاع باز است — تصویر بلند سربرگ را می‌کشد')
        self.assertIn('object-fit: contain', rule)

    def test_the_page_emblem_has_a_height_ceiling(self):
        rule = self._rule('.pres-wcu')
        self.assertIn('max-block-size', rule)
        self.assertIn('object-fit: contain', rule)


class EmblemSizeIsPinnedOnTheTagTests(TestCase):
    """اندازهٔ نشان نباید به رسیدن فایل CSS وابسته باشد.

    سه بار اصلاح CSS به سرور نرسید و تصویر ۱۰۲۴ پیکسلی هر بار سربرگ
    را ترکاند. صفت style روی خود تگ، حتی با شیوه‌نامهٔ کهنه هم
    درست می‌ماند.
    """

    def _template(self, name):
        from pathlib import Path
        from django.conf import settings
        return (Path(settings.BASE_DIR) / 'templates' / name).read_text(
            encoding='utf-8')

    def test_the_header_emblem_carries_its_own_size(self):
        html = self._template('base.html')
        pinned = html.count('style="width:64px;height:64px;object-fit:contain;')
        self.assertEqual(pinned, 2, 'هر دو نشان سربرگ اندازهٔ خودشان را ندارند')

    def test_the_page_emblem_carries_its_own_ceiling(self):
        html = self._template('core/presidency.html')
        self.assertIn('max-width:290px;max-height:290px;object-fit:contain;', html)


class SettingsImagePreviewTests(TestCase):
    """سه فیلد تصویری باید از هم قابل تشخیص باشند."""

    def _admin(self):
        from django.contrib.admin.sites import AdminSite
        from core.admin import SiteSettingsAdmin
        from core.models import SiteSettings
        return SiteSettingsAdmin(SiteSettings, AdminSite())

    def test_each_field_has_a_preview_beside_it(self):
        listed = []
        for _title, opts in self._admin().fieldsets:
            listed.extend(opts['fields'])
        for name in ('logo_preview', 'favicon_preview',
                     'world_class_logo_preview'):
            self.assertIn(name, listed)

    def test_previews_are_read_only(self):
        readonly = self._admin().get_readonly_fields(None, None)
        self.assertIn('logo_preview', readonly)
        self.assertIn('world_class_logo_preview', readonly)

    def test_an_empty_field_says_so_instead_of_breaking(self):
        from core.models import SiteSettings
        admin_obj = self._admin()
        admin_obj.instance_for_preview = SiteSettings()
        self.assertIn('آپلود نشده', admin_obj.logo_preview())

    def test_a_missing_file_is_reported_not_raised(self):
        """photo.width فایل را باز می‌کند؛ نبودنش نباید صفحه را بشکند."""
        from core.models import SiteSettings
        admin_obj = self._admin()
        admin_obj.instance_for_preview = SiteSettings(logo='site/gone.png')
        self.assertIn('پیدا نشد', admin_obj.logo_preview())

    def test_no_instance_yet_is_handled(self):
        admin_obj = self._admin()
        admin_obj.instance_for_preview = None
        self.assertIn('آپلود نشده', admin_obj.favicon_preview())


class OrgChartFullScreenTests(TestCase):
    """چارت سازمانی باید تمام‌صفحهٔ همان دستگاه باز شود."""

    def _about(self):
        from core.models import SiteSettings
        SiteSettings.objects.all().delete()
        SiteSettings.objects.create(org_chart_file='site/org_chart/chart.png')
        return self.client.get(reverse('core:about')).content.decode()

    def _asset(self, name):
        from pathlib import Path
        from django.conf import settings
        return (Path(settings.BASE_DIR) / 'static' / name).read_text(
            encoding='utf-8')

    def test_the_chart_is_marked_zoomable(self):
        html = self._about()
        self.assertIn('data-zoomable', html)
        self.assertIn('org-chart-img', html)

    def test_the_button_opens_the_same_image(self):
        html = self._about()
        self.assertIn('data-zoom-open=".org-chart-img"', html)

    def test_the_old_new_tab_link_is_gone(self):
        """باز کردن فایل در تب تازه یعنی خروج از سایت و برگشت با back."""
        html = self._about()
        chart = html.split('org-chart-file')[1].split('</div>')[0]
        self.assertNotIn('target="_blank"', chart)

    def test_downloading_is_still_offered(self):
        self.assertIn('دانلود', self._about())

    def test_the_viewer_asks_for_real_full_screen(self):
        js = self._asset('js/main.js')
        self.assertIn('requestFullscreen', js)
        # سافاری آیفون روی عنصر غیرویدیویی نمی‌دهد؛ پوشش fixed جایش
        self.assertIn('zoom-overlay', js)

    def test_leaving_full_screen_closes_the_overlay(self):
        """وگرنه یک تصویر تمام‌صفحه بدون راه خروج می‌ماند."""
        js = self._asset('js/main.js')
        self.assertIn('fullscreenchange', js)

    def test_escape_closes_it(self):
        js = self._asset('js/main.js')
        block = js[js.index('zoom-overlay'):]
        self.assertIn("e.key === 'Escape'", block)

    def test_the_overlay_uses_small_viewport_units(self):
        """vh روی موبایل نوار آدرس را هم حساب می‌کند."""
        css = self._asset('css/main.css')
        start = css.index(chr(10) + '.zoom-image {') + 1
        rule = css[start:css.index('}', start)]
        self.assertIn('svh', rule)
        self.assertNotIn('100vh', rule)


class GraduateGroupMatchingTests(TestCase):
    """نام واقعی گروه با کلیدواژهٔ سند یکی نیست."""

    def _group(self, name, **extra):
        # گروه بدون دانشکده ساخته نمی‌شود؛ یکی مشترک برای همهٔ تست‌ها
        from academics.models import AcademicGroup, Department
        from django.utils.text import slugify
        department, _ = Department.objects.get_or_create(
            slug='dept-test', defaults={'name': 'دانشکدهٔ آزمایشی'})
        return AcademicGroup.objects.create(
            name=name, slug=slugify(name, allow_unicode=True),
            department=department, **extra)

    def _run(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('set_graduate_groups', stdout=out)
        return out.getvalue()

    def setUp(self):
        from academics.models import AcademicGroup
        AcademicGroup.objects.all().delete()

    def test_a_longer_real_name_still_matches(self):
        """سند «بازرگانی» نوشته و نام واقعی «گروه مدیریت بازرگانی» است."""
        from academics.models import AcademicGroup
        self._group('گروه مدیریت بازرگانی')
        self._run()
        self.assertTrue(AcademicGroup.objects.first().has_graduate)

    def test_all_four_from_the_document_are_found(self):
        from academics.models import AcademicGroup
        for name in ('گروه مدیریت بازرگانی', 'گروه مدیریت صنعتی و مالی',
                     'گروه علوم تربیتی - مدیریت آموزشی', 'گروه حسابداری'):
            self._group(name)
        self._run()
        self.assertEqual(
            AcademicGroup.objects.filter(has_graduate=True).count(), 4)

    def test_the_document_order_is_kept(self):
        from academics.models import AcademicGroup
        self._group('گروه حسابداری')
        self._group('گروه مدیریت بازرگانی')
        self._run()
        marked = list(AcademicGroup.objects.filter(has_graduate=True)
                      .order_by('graduate_order').values_list('name', flat=True))
        self.assertEqual(marked[0], 'گروه مدیریت بازرگانی')

    def test_an_unrelated_group_is_left_alone(self):
        from academics.models import AcademicGroup
        self._group('گروه مکانیک')
        self._run()
        self.assertFalse(AcademicGroup.objects.get(name='گروه مکانیک').has_graduate)

    def test_a_stale_mark_is_removed(self):
        from academics.models import AcademicGroup
        self._group('گروه مکانیک', has_graduate=True)
        self._run()
        self.assertFalse(AcademicGroup.objects.get(name='گروه مکانیک').has_graduate)

    def test_running_twice_keeps_the_same_four(self):
        """پاک‌سازی نباید همان‌هایی را بردارد که تازه علامت خورده‌اند."""
        from academics.models import AcademicGroup
        for name in ('گروه مدیریت بازرگانی', 'گروه مدیریت صنعتی و مالی',
                     'گروه علوم تربیتی - مدیریت آموزشی', 'گروه حسابداری'):
            self._group(name)
        self._run()
        self._run()
        self.assertEqual(
            AcademicGroup.objects.filter(has_graduate=True).count(), 4)

    def test_each_keyword_takes_a_different_group(self):
        """دو کلیدواژه نباید به یک گروه بچسبند."""
        from academics.models import AcademicGroup
        self._group('گروه مدیریت صنعتی و مالی')
        self._group('گروه مدیریت بازرگانی')
        self._run()
        marked = AcademicGroup.objects.filter(has_graduate=True)
        self.assertEqual(marked.count(), 2)
        self.assertEqual(len({g.graduate_order for g in marked}), 2)


class RevisionInspectorTests(TestCase):
    """بازرس باید روی همان چیزی بسنجد که کاربر می‌بیند."""

    def _report(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('check_revisions', stdout=out)
        return out.getvalue()

    def test_it_lists_all_eighteen(self):
        report = self._report()
        for number in range(1, 19):
            self.assertIn('%2d.' % number, report)

    def test_it_ends_with_a_tally(self):
        self.assertIn('از 18 بند', self._report())

    def test_it_reports_an_empty_database_without_crashing(self):
        from core.models import PresidencyOffice, SiteSettings
        PresidencyOffice.objects.all().delete()
        SiteSettings.objects.all().delete()
        self.assertIn('وضعیت بندهای سند اصلاحات', self._report())

    def test_the_menu_items_are_seen_as_done(self):
        """بندهای ۱۳ تا ۱۶ در قالب‌اند و به داده وابسته نیستند."""
        report = self._report()
        for number in (13, 14, 15, 16):
            line = [ln for ln in report.splitlines()
                    if ln.strip().startswith(('✓ %d.' % number,
                                              '✗ %d.' % number,
                                              '✓ %2d.' % number,
                                              '✗ %2d.' % number))]
            self.assertTrue(line, 'بند %d گزارش نشد' % number)
            self.assertTrue(line[0].lstrip().startswith('✓'),
                            'بند %d انجام‌نشده گزارش شد: %s' % (number, line[0]))
