"""صفحهٔ دانشکده‌ها — سند PDF موسسه، و آیتمش در نوار بالا.

پیش از این این صفحه ساختار را از دیتابیس می‌ساخت و درختی نشان
می‌داد؛ موسسه خواست به‌جایش همان فایلی بیاید که خودش تهیه کرده.
آزمون‌های آن درخت با خودش برداشته شدند.
"""
import shutil
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import SiteSettings

MEDIA = tempfile.mkdtemp(prefix='faculties-doc-')


@override_settings(MEDIA_ROOT=MEDIA)
class FacultiesDocumentPageTests(TestCase):
    """صفحه فقط یک چیز نشان می‌دهد: سند رسمی."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        folder = Path(MEDIA) / 'site' / 'faculties'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'reshte-ha.pdf').write_bytes(b'%PDF-1.4 fake')
        self.settings_row = SiteSettings.objects.create(
            university_name_fa='موسسه آموزش عالی علامه امینی',
            faculties_pdf='site/faculties/reshte-ha.pdf')

    def _html(self):
        return self.client.get(
            reverse('academics:departments')).content.decode()

    def test_the_page_opens(self):
        self.assertEqual(
            self.client.get(reverse('academics:departments')).status_code, 200)

    def test_the_file_is_shown_in_the_page(self):
        """بازدیدکننده نباید مجبور باشد اول دانلود کند."""
        html = self._html()
        self.assertIn('doc-frame', html)
        self.assertIn('reshte-ha.pdf', html)

    def test_it_can_also_be_downloaded(self):
        block = self._html().split('doc-actions')[1].split('</span>')[0]
        self.assertIn('download', block)

    def test_a_browser_that_cannot_frame_it_is_told_what_to_do(self):
        """بعضی مرورگرهای موبایل PDF را داخل قاب نشان نمی‌دهند."""
        self.assertIn('doc-fallback', self._html())

    def test_the_old_tree_is_gone(self):
        html = self._html()
        for marker in ('class="trunk"', 'class="bough', 'tree-summary',
                       'data-tree-filter'):
            self.assertNotIn(marker, html)

    def test_no_file_does_not_leave_a_visitor_on_a_blank_page(self):
        self.settings_row.faculties_pdf = ''
        self.settings_row.save(update_fields=['faculties_pdf'])
        cache.clear()
        html = self._html()
        self.assertNotIn('doc-frame', html)
        self.assertIn('هنوز روی سایت قرار نگرفته', html)
        self.assertIn(reverse('academics:majors'), html)

    def test_no_file_tells_staff_where_to_put_one(self):
        """آدرس پنل به کار بازدیدکننده نمی‌آید، به کار مدیر می‌آید."""
        from django.contrib.auth import get_user_model

        self.settings_row.faculties_pdf = ''
        self.settings_row.save(update_fields=['faculties_pdf'])
        cache.clear()
        self.assertNotIn('/admin/core/sitesettings/', self._html())

        staff = get_user_model().objects.create_user(
            username='karmand', password='x', is_staff=True)
        self.client.force_login(staff)
        cache.clear()
        self.assertIn('/admin/core/sitesettings/', self._html())

    def test_a_recorded_but_absent_file_is_not_framed(self):
        """نام فایل در دیتابیس، دلیل بودنش روی دیسک نیست."""
        self.settings_row.faculties_pdf = 'site/faculties/gone.pdf'
        self.settings_row.save(update_fields=['faculties_pdf'])
        cache.clear()
        self.assertNotIn('doc-frame', self._html())

    def test_no_settings_row_still_renders(self):
        SiteSettings.objects.all().delete()
        cache.clear()
        self.assertEqual(
            self.client.get(reverse('academics:departments')).status_code, 200)

    def test_the_panel_offers_the_upload(self):
        from core.admin import SiteSettingsAdmin

        self.assertIn('faculties_pdf', str(SiteSettingsAdmin.fieldsets))

    def test_only_a_pdf_is_accepted(self):
        field = SiteSettings._meta.get_field('faculties_pdf')
        allowed = set()
        for validator in field.validators:
            allowed |= set(getattr(validator, 'allowed_extensions', []))
        self.assertEqual(allowed, {'pdf'})


class FacultiesMenuItemTests(TestCase):
    """آیتم «دانشکده‌ها» پیش از گروه‌های آموزشی."""

    def setUp(self):
        cache.clear()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def test_the_item_exists(self):
        nav = self._nav()
        self.assertIn(reverse('academics:departments'), nav)
        self.assertIn('دانشکده‌ها', nav)

    def test_it_sits_before_the_groups(self):
        nav = self._nav()
        faculties = nav.index(reverse('academics:departments'))
        groups = nav.index('گروه های آموزشی')
        self.assertLess(faculties, groups)

    def test_the_affiliated_units_label_is_gone(self):
        """موسسه خواست این عبارت از زیرمنوی حوزه ریاست برداشته شود."""
        self.assertNotIn('واحدهای وابسته', self._nav())

    def test_its_children_survived_the_label(self):
        nav = self._nav()
        self.assertIn(reverse('core:public_relations'), nav)
        self.assertIn(reverse('core:security_office'), nav)
