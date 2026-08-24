"""صفحهٔ ریاست موسسه — مطابق سند اصلاحات موسسه."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import PresidencyOffice, SiteSettings


class PresidencyPageTests(TestCase):
    """آنچه صفحه باید نشان دهد — و آنچه نباید."""

    @classmethod
    def setUpTestData(cls):
        cls.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_title='استاد گروه مدیریت صنعتی و فناوری اطلاعات',
            president_message='دانشگاه جایی برای ساختن است.',
            president_bio='متن معرفی.',
            president_education='دکتری مدیریت صنعتی\nکارشناسی ارشد صنایع',
            president_resume='رئیس موسسه\nمدیر گروه صنایع',
            president_email='president@portal.aab.ac.ir',
            president_phone='01135333333',
            president_website='https://WCM-Society.Com',
            office_address='بابلسر، خیابان شهید بهشتی',
            office_hours='شنبه تا پنج‌شنبه',
        )

    def _html(self):
        return self.client.get(reverse('core:presidency')).content.decode()

    def test_page_opens(self):
        self.assertEqual(
            self.client.get(reverse('core:presidency')).status_code, 200)

    def test_the_portrait_carries_the_name(self):
        html = self._html()
        self.assertIn('pres-portrait', html)
        self.assertIn('دکتر حسن فارسیجانی', html)

    def test_message_and_bio_are_gone(self):
        """سند اصلاحات خواست جز «ارتباط با ریاست» چیزی نماند."""
        html = self._html()
        self.assertNotIn('دانشگاه جایی برای ساختن است.', html)
        self.assertNotIn('متن معرفی.', html)

    def test_history_lists_are_gone(self):
        html = self._html()
        self.assertNotIn('مدیر گروه صنایع', html)
        self.assertNotIn('pres-timeline', html)

    def test_the_fields_are_kept_in_the_database(self):
        """حذف از صفحه نباید یعنی حذف از پنل — داده باید بماند."""
        office = PresidencyOffice.objects.first()
        self.assertEqual(office.president_bio, 'متن معرفی.')
        self.assertTrue(office.education_list)

    def test_contact_items_are_horizontal_and_coloured(self):
        html = self._html()
        self.assertIn('pres-row', html)
        for tile in ('pres-tile-1', 'pres-tile-2', 'pres-tile-3', 'pres-tile-4'):
            self.assertIn(tile, html)

    def test_visiting_days_and_floor_are_shown(self):
        html = self._html()
        self.assertIn('روزهای مراجعه', html)
        self.assertIn('شنبه تا پنج‌شنبه', html)
        self.assertIn('طبقهٔ سوم', html)

    def test_the_website_shows_as_a_bare_latin_url(self):
        """«زنجیره تأمین» باید برداشته شده باشد و خودِ نشانی بماند."""
        self.office.president_website_label = 'انجمن مدیریت زنجیره تأمین'
        self.office.save(update_fields=['president_website_label'])
        html = self._html()
        self.assertIn('https://WCM-Society.Com', html)
        self.assertNotIn('زنجیره تأمین', html)
        self.assertIn('dir="ltr"', html)

    def test_the_phone_contact_download_is_gone(self):
        html = self._html()
        self.assertNotIn('افزودن به مخاطبان', html)
        self.assertNotIn('.vcf', html)

    def test_the_vcard_route_no_longer_exists(self):
        from django.urls import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('core:presidency_vcard')

    def test_the_world_class_logo_appears_when_uploaded(self):
        SiteSettings.objects.all().delete()
        SiteSettings.objects.create(world_class_logo='site/wcu.png')
        html = self._html()
        self.assertIn('pres-wcu', html)
        self.assertIn('site/wcu.png', html)

    def test_no_logo_means_no_broken_image(self):
        SiteSettings.objects.all().delete()
        SiteSettings.objects.create()
        self.assertNotIn('pres-wcu"', self._html())

    def test_structured_data_is_valid_json(self):
        import json
        html = self._html()
        blocks = [chunk.split('</script>')[0]
                  for chunk in html.split('application/ld+json">')[1:]]
        people = [json.loads(b) for b in blocks if '"Person"' in b]
        self.assertEqual(len(people), 1, 'بلوک Person پیدا نشد')
        self.assertEqual(people[0]['name'], 'دکتر حسن فارسیجانی')

    def test_page_survives_an_empty_record(self):
        PresidencyOffice.objects.all().delete()
        PresidencyOffice.objects.create()
        self.assertEqual(
            self.client.get(reverse('core:presidency')).status_code, 200)

    def test_missing_photo_file_does_not_break_the_page(self):
        office = PresidencyOffice.objects.first()
        office.president_photo = 'presidency/does-not-exist.jpg'
        office.save(update_fields=['president_photo'])
        self.assertIsNone(office.photo_size)
        self.assertEqual(
            self.client.get(reverse('core:presidency')).status_code, 200)


class PresidentCvSeedTests(TestCase):
    """رزومهٔ رسمی باید در پنل بنشیند و ویرایش ادمین را پاک نکند."""

    def test_it_fills_an_empty_record(self):
        PresidencyOffice.objects.create()
        call_command('seed_president_cv', stdout=StringIO())
        office = PresidencyOffice.objects.first()
        self.assertEqual(office.president_name, 'دکتر حسن فارسیجانی')
        self.assertIn('برادفورد', office.president_education)
        self.assertGreaterEqual(len(office.resume_list), 8)

    def test_it_creates_the_record_when_none_exists(self):
        PresidencyOffice.objects.all().delete()
        call_command('seed_president_cv', stdout=StringIO())
        self.assertEqual(PresidencyOffice.objects.count(), 1)

    def test_it_leaves_an_admin_edit_alone(self):
        PresidencyOffice.objects.create(president_title='عنوان دستی')
        call_command('seed_president_cv', stdout=StringIO())
        self.assertEqual(PresidencyOffice.objects.first().president_title,
                         'عنوان دستی')

    def test_replace_overrides_on_request(self):
        PresidencyOffice.objects.create(president_title='عنوان دستی')
        call_command('seed_president_cv', '--replace', stdout=StringIO())
        self.assertIn('مدیریت صنعتی',
                      PresidencyOffice.objects.first().president_title)

    def test_replace_clears_the_website_label(self):
        """برچسب «زنجیره تأمین» باید برود و خودِ نشانی بماند."""
        PresidencyOffice.objects.create(
            president_website_label='انجمن مدیریت زنجیره تأمین')
        call_command('seed_president_cv', '--replace', stdout=StringIO())
        self.assertEqual(
            PresidencyOffice.objects.first().president_website_label, '')

    def test_running_twice_changes_nothing_the_second_time(self):
        PresidencyOffice.objects.create()
        call_command('seed_president_cv', stdout=StringIO())
        out = StringIO()
        call_command('seed_president_cv', stdout=out)
        self.assertIn('چیزی برای تغییر نبود', out.getvalue())


class PresidencyAdminTests(TestCase):
    """هر چیزی که روی صفحه دیده می‌شود باید در ادمین قابل ویرایش باشد."""

    def test_every_president_field_is_in_a_fieldset(self):
        from core.admin import PresidencyOfficeAdmin
        listed = set()
        for _title, opts in PresidencyOfficeAdmin.fieldsets:
            listed.update(opts['fields'])
        for field in ('president_website', 'president_cv', 'president_research',
                      'president_education', 'president_resume'):
            self.assertIn(field, listed, '%s در ادمین دیده نمی‌شود' % field)

    def test_the_world_class_logo_is_editable(self):
        from core.admin import SiteSettingsAdmin
        listed = set()
        for _title, opts in SiteSettingsAdmin.fieldsets:
            listed.update(opts['fields'])
        self.assertIn('world_class_logo', listed)
