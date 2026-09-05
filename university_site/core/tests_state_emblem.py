"""ارم الله باید از پنل قابل آپلود باشد.

تا امروز یک فایل ثابت در پوشهٔ static بود: عوض‌کردنش یعنی ویرایش کد
و یک دیپلوی کامل — کاری که موسسه از پنل نمی‌توانست انجام دهد.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings


class TheEmblemComesFromThePanelTests(TestCase):

    def setUp(self):
        cache.clear()
        SiteSettings.objects.all().delete()

    def _banner(self):
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('bnr-state')[1].split('</span>')[-2] \
            if 'bnr-state' in html else ''

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_default_emblem_shows_when_none_is_uploaded(self):
        SiteSettings.objects.create(university_name_fa='موسسه')
        self.assertIn('images/mark-iran.png', self._html())

    def test_an_uploaded_emblem_replaces_it(self):
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    state_emblem='site/allah.png')
        html = self._html()
        self.assertIn('site/allah.png', html)
        self.assertNotIn('images/mark-iran.png', html)

    def test_clearing_it_brings_the_default_back(self):
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          state_emblem='site/allah.png')
        row.state_emblem = ''
        row.save()
        self.assertIn('images/mark-iran.png', self._html())

    def test_the_header_is_never_left_without_an_emblem(self):
        """حتی وقتی هیچ ردیف تنظیماتی نیست."""
        self.assertFalse(SiteSettings.objects.exists())
        self.assertIn('images/mark-iran.png', self._html())

    def test_it_keeps_its_size_on_the_tag(self):
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    state_emblem='site/allah.png')
        tag = self._html().split('site/allah.png')[1].split('>')[0]
        self.assertIn('width="182"', tag)
        self.assertIn('height="198"', tag)

    def test_it_is_decorative_for_screen_readers(self):
        """متن «جمهوری اسلامی ایران» کنارش هست؛ نشان تکرارش نکند."""
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    state_emblem='site/allah.png')
        tag = self._html().split('site/allah.png')[1].split('>')[0]
        self.assertIn('aria-hidden="true"', tag)


class TheEmblemIsEditableInTheAdminTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modiremblem', 'e@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)
        self.row = SiteSettings.objects.create(university_name_fa='موسسه')

    def _form(self):
        return self.client.get(
            '/admin/core/sitesettings/%d/change/' % self.row.pk
        ).content.decode()

    def test_the_upload_box_is_on_the_form(self):
        html = self._form()
        self.assertIn('name="state_emblem"', html)
        self.assertIn('ارم الله', html)

    def test_it_can_be_cleared_from_the_form(self):
        self.row.state_emblem = 'site/allah.png'
        self.row.save()
        self.assertIn('state_emblem-clear', self._form())

    def test_it_has_a_preview_like_the_other_images(self):
        from core.admin import SiteSettingsAdmin

        self.assertIn('state_emblem', SiteSettingsAdmin.LOGO_FIELDS)
        self.assertIn('state_emblem_preview',
                      str(SiteSettingsAdmin.fieldsets))

    def test_the_preview_is_read_only(self):
        from core.admin import SiteSettingsAdmin

        admin = SiteSettingsAdmin(SiteSettings, None)
        self.assertIn('state_emblem_preview',
                      admin.get_readonly_fields(None, self.row))

    def test_a_missing_file_does_not_break_the_form(self):
        """بعد از انتقال مدیا پیش می‌آید؛ فرم نباید ۵۰۰ بدهد."""
        self.row.state_emblem = 'site/gone.png'
        self.row.save()
        self.assertIn('پیدا نشد', self._form())


class ABigUploadIsShrunkTests(TestCase):
    """این نشان در سربرگِ هر صفحه و زودهنگام بار می‌شود."""

    def test_only_the_emblem_is_shrunk(self):
        limits = SiteSettings.shrink_images
        self.assertEqual(list(limits), ['state_emblem'])
        self.assertLessEqual(limits['state_emblem'], 600)

    def test_the_favicon_is_left_alone(self):
        """کوچک‌کردن فاویکون خرابش می‌کند."""
        self.assertNotIn('favicon', SiteSettings.shrink_images)
        self.assertNotIn('logo', SiteSettings.shrink_images)


class ABlackBackgroundBecomesTransparentTests(TestCase):
    """نشانی که از اینترنت می‌آید معمولاً JPEG با پس‌زمینهٔ توپر است.

    چنین فایلی در سربرگ یک مربع سیاه می‌شود و مدیر سایت راهی برای
    درست‌کردنش ندارد جز ساختن فایل با ویرایشگر گرافیکی.
    """

    def _emblem(self, background=(0, 0, 0), fmt='JPEG'):
        """نشانی شبیه ارم الله: پس‌زمینه، حلقهٔ طلایی، دایرهٔ تیرهٔ داخلی."""
        import io as _io

        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from PIL import Image, ImageDraw

        image = Image.new('RGB', (200, 200), background)
        draw = ImageDraw.Draw(image)
        draw.ellipse((10, 10, 190, 190), fill=(212, 160, 23))
        draw.ellipse((35, 35, 165, 165), fill=background)
        draw.ellipse((70, 70, 130, 130), fill=(212, 160, 23))
        buffer = _io.BytesIO()
        image.save(buffer, fmt)
        name = default_storage.save(
            'site/probe.%s' % ('jpg' if fmt == 'JPEG' else 'png'),
            ContentFile(buffer.getvalue()))
        self.addCleanup(default_storage.delete, name)
        return name

    def _saved(self, name):
        import io as _io

        from django.core.files.storage import default_storage
        from PIL import Image

        row = SiteSettings.objects.create(university_name_fa='موسسه')
        row.state_emblem.name = name
        row.save()
        self.addCleanup(
            lambda: default_storage.exists(row.state_emblem.name)
            and default_storage.delete(row.state_emblem.name))
        with default_storage.open(row.state_emblem.name, 'rb') as handle:
            return row, Image.open(_io.BytesIO(handle.read())).convert('RGBA')

    def test_the_black_square_is_gone(self):
        _, image = self._saved(self._emblem())
        self.assertEqual(image.getpixel((2, 2))[3], 0)

    def test_the_emblem_itself_survives(self):
        """جایگزینیِ سراسریِ سیاه، دایرهٔ داخلی نشان را هم سوراخ می‌کرد."""
        _, image = self._saved(self._emblem())
        self.assertEqual(image.getpixel((100, 45))[3], 255)   # حلقهٔ طلایی
        self.assertEqual(image.getpixel((100, 50))[3], 255)   # سیاهِ داخلی

    def test_it_is_stored_as_png(self):
        row, _ = self._saved(self._emblem())
        self.assertTrue(row.state_emblem.name.endswith('.png'))

    def test_a_white_background_works_the_same(self):
        _, image = self._saved(self._emblem(background=(255, 255, 255)))
        self.assertEqual(image.getpixel((2, 2))[3], 0)

    def test_an_already_transparent_file_is_left_alone(self):
        import io as _io

        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from PIL import Image

        image = Image.new('RGBA', (60, 60), (0, 0, 0, 0))
        image.paste((212, 160, 23, 255), (10, 10, 50, 50))
        buffer = _io.BytesIO()
        image.save(buffer, 'PNG')
        name = default_storage.save('site/clear.png',
                                    ContentFile(buffer.getvalue()))
        self.addCleanup(
            lambda: default_storage.exists(name)
            and default_storage.delete(name))

        from core.imaging import drop_flat_background

        row = SiteSettings.objects.create(university_name_fa='موسسه')
        row.state_emblem.name = name
        self.assertFalse(drop_flat_background(row.state_emblem))

    def test_a_busy_photo_is_left_alone(self):
        """گوشه‌های ناهم‌رنگ یعنی پس‌زمینهٔ یکدستی نیست؛ حدس ممنوع."""
        import io as _io

        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from PIL import Image, ImageDraw

        image = Image.new('RGB', (100, 100), (10, 10, 10))
        ImageDraw.Draw(image).rectangle((0, 0, 49, 49), fill=(240, 30, 90))
        buffer = _io.BytesIO()
        image.save(buffer, 'JPEG')
        name = default_storage.save('site/busy.jpg',
                                    ContentFile(buffer.getvalue()))
        self.addCleanup(
            lambda: default_storage.exists(name)
            and default_storage.delete(name))

        from core.imaging import drop_flat_background

        row = SiteSettings.objects.create(university_name_fa='موسسه')
        row.state_emblem.name = name
        self.assertFalse(drop_flat_background(row.state_emblem))

    def test_no_file_is_harmless(self):
        from core.imaging import drop_flat_background

        self.assertFalse(drop_flat_background(None))
