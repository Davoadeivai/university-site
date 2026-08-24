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
