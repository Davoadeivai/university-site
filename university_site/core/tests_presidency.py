"""صفحهٔ ریاست موسسه — مطابق سند اصلاحات موسسه."""
import re
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

    def test_the_old_timeline_markup_is_gone(self):
        """سوابق حالا کارت رنگی‌اند، نه خط زمانی تک‌ستونی."""
        self.assertNotIn('pres-timeline', self._html())

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
        self.office.office_floor = 'طبقهٔ سوم'
        self.office.save(update_fields=['office_floor'])
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
        for field in ('president_website', 'president_highlights',
                      'president_research', 'president_education',
                      'president_resume', 'president_teaching',
                      'president_awards', 'president_memberships'):
            self.assertIn(field, listed, '%s در ادمین دیده نمی‌شود' % field)

    def test_the_world_class_logo_is_editable(self):
        from core.admin import SiteSettingsAdmin
        listed = set()
        for _title, opts in SiteSettingsAdmin.fieldsets:
            listed.update(opts['fields'])
        self.assertIn('world_class_logo', listed)


class PresidencyResumeTests(TestCase):
    """رزومه فقط یک فایل قابل دانلود است، نه شش کارت روی صفحه."""

    @classmethod
    def setUpTestData(cls):
        NL = chr(10)
        cls.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_title='استاد گروه مدیریت صنعتی',
            president_education=NL.join(['دکتری برادفورد', 'ارشد تربیت مدرس']),
            president_resume=NL.join(['رئیس موسسه', 'مشاور ایران‌خودرو']),
            president_teaching='مدیریت تولید',
            president_awards='استاد نمونه',
            president_memberships='سردبیر چشم‌انداز',
            president_research='مدیریت در کلاس جهانی',
            president_highlights='۳۱ | جلد کتاب',
            president_website='https://WCM-Society.Com',
            president_cv='presidency/cv/farsijani.pdf',
            office_floor='طبقهٔ سوم',
            office_hours='شنبه تا پنج‌شنبه',
        )

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def _html(self):
        return self.client.get(reverse('core:presidency')).content.decode()

    def test_the_six_cards_are_gone(self):
        """موسسه خواست سوابق از صفحه برداشته شود."""
        html = self._html()
        self.assertNotIn('pres-cv-grid', html)
        for tone in range(1, 7):
            self.assertNotIn('pres-tone-%d' % tone, html)

    def test_none_of_the_section_text_leaks_onto_the_page(self):
        html = self._html()
        for text in ('دکتری برادفورد', 'مشاور ایران‌خودرو', 'مدیریت تولید',
                     'استاد نمونه', 'سردبیر چشم‌انداز'):
            self.assertNotIn(text, html)

    def test_the_statistics_are_gone_too(self):
        self.assertNotIn('pres-stat', self._html())

    def test_the_download_button_is_offered(self):
        html = self._html()
        self.assertIn('pres-cv-btn', html)
        self.assertIn('farsijani.pdf', html)
        self.assertIn('دانلود رزومه', html)

    def test_the_button_actually_downloads(self):
        """بدون download، PDF در تب باز می‌شود و کاربر فایل را نمی‌گیرد."""
        html = self._html()
        button = html.split('pres-cv-btn')[1].split('</a>')[0]
        self.assertIn('download', button)

    def test_no_file_means_no_button(self):
        self.office.president_cv = ''
        self.office.save(update_fields=['president_cv'])
        self.assertNotIn('pres-cv-btn', self._html())

    def test_word_files_are_accepted(self):
        """موسسه خواست PDF یا Word."""
        field = PresidencyOffice._meta.get_field('president_cv')
        allowed = set()
        for validator in field.validators:
            allowed |= set(getattr(validator, 'allowed_extensions', []))
        self.assertTrue({'pdf', 'doc', 'docx'} <= allowed)

    def test_the_fields_are_kept_for_the_panel(self):
        """برداشتن از صفحه نباید یعنی پاک‌کردن از پنل."""
        office = PresidencyOffice.objects.first()
        self.assertTrue(office.education_list)
        self.assertTrue(office.resume_list)

    def test_the_floor_comes_from_the_record(self):
        """قالب «طبقهٔ سوم» را ثابت نوشته بود و نشانی «دوم» می‌گفت."""
        html = self._html()
        self.assertIn('طبقهٔ سوم', html)

        self.office.office_floor = 'طبقهٔ چهارم'
        self.office.save(update_fields=['office_floor'])
        from django.core.cache import cache
        cache.clear()
        html = self._html()
        self.assertIn('طبقهٔ چهارم', html)
        self.assertNotIn('طبقهٔ سوم', html)

    def test_an_empty_floor_does_not_print_a_lie(self):
        self.office.office_floor = ''
        self.office.save(update_fields=['office_floor'])
        html = self._html()
        self.assertNotIn('طبقهٔ سوم', html)


class WcuPlaqueTests(TestCase):
    """لوح کلاس جهانی — نشان، عنوان، شعار و نشانی، به همین ترتیب."""

    @classmethod
    def setUpTestData(cls):
        cls.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_title='استاد گروه مدیریت صنعتی و فناوری اطلاعات',
            president_education='دکتری برادفورد',
            wcu_title='سایت تخصصی مدیریت کلاس جهانی',
            wcu_motto='چگونگی تبدیل دانشگاه‌ها به سازمان در کلاس جهانی',
            president_website='https://WCM-Society.Com',
        )
        SiteSettings.objects.all().delete()
        SiteSettings.objects.create(world_class_logo='site/wcu.png')

    def _html(self):
        from django.core.cache import cache
        # نشان از site_settings می‌آید و آن ۶۰ ثانیه کش می‌شود
        cache.clear()
        return self.client.get(reverse('core:presidency')).content.decode()

    def test_the_order_is_emblem_title_motto_address(self):
        html = self._html()
        for earlier, later in (('pres-wcu', 'wcu-title'),
                               ('wcu-title', 'wcu-motto'),
                               ('wcu-motto', 'wcu-link')):
            self.assertLess(html.index(earlier), html.index(later),
                            '%s باید پیش از %s بیاید' % (earlier, later))

    def test_the_resume_comes_after_the_plaque(self):
        html = self._html()
        self.assertLess(html.index('wcu-plaque'), html.index('pres-tile'))

    def test_the_motto_is_quoted_by_css_not_by_hand(self):
        """اگر ادمین گیومه بگذارد، دو تا می‌شود."""
        html = self._html()
        self.assertNotIn('«چگونگی تبدیل', html)
        css = _css_text()
        start = css.index(chr(10) + '.wcu-motto::before') + 1
        self.assertIn('«', css[start:start + 60])

    def test_an_empty_plaque_is_not_drawn(self):
        PresidencyOffice.objects.all().delete()
        SiteSettings.objects.all().delete()
        PresidencyOffice.objects.create(president_name='رئیس')
        SiteSettings.objects.create()
        self.assertNotIn('wcu-plaque', self._html())

    def test_the_stat_cards_are_gone(self):
        """موسسه خواست سه کارت عددی برداشته شود."""
        html = self._html()
        self.assertNotIn('pres-stats', html)
        self.assertNotIn('pres-stat-num', html)

    def test_the_stat_styling_left_with_them(self):
        css = _css_text()
        self.assertNotIn('.pres-stat', css)
        self.assertNotIn('.pres-site', css)

    def test_the_name_outweighs_the_section_titles(self):
        """چشم باید از نام شروع کند، نه از تیتر بخش‌ها."""
        css = _css_text()
        title = _rule(css, '.pres-cv-title')
        card = _rule(css, '.pres-cv-card-title')
        self.assertIn('clamp(26px', title)
        self.assertIn('font-size: 16.5px', card)

    def test_the_title_and_subtitle_carry_their_own_colour(self):
        css = _css_text()
        self.assertIn('color: #33101a', _rule(css, '.pres-cv-title'))
        self.assertIn('color: #8a1f2b', _rule(css, '.pres-cv-sub'))

    def test_both_themes_are_covered(self):
        css = _css_text()
        for selector in ('.wcu-title', '.wcu-motto', '.pres-cv-title'):
            self.assertIn('[data-theme="dark"] %s' % selector, css,
                          '%s نسخهٔ تیره ندارد' % selector)


class PresidencyMenuLabelTests(TestCase):
    """در حوزهٔ ریاست، «ریاست موسسه» باید فقط «ریاست» باشد."""

    def test_the_menu_item_is_shortened(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('>ریاست</a>', html)
        self.assertNotIn('>ریاست موسسه</a>', html)


def _css_text():
    from pathlib import Path
    from django.conf import settings
    return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
        encoding='utf-8')


def _rule(css, selector):
    start = css.index(chr(10) + selector + ' {') + 1
    return css[start:css.index('}', start)]


class PresidencyProportionTests(TestCase):
    """اندازهٔ عکس و فاصلهٔ زیر نشان."""

    def _rule(self, selector):
        from pathlib import Path
        from django.conf import settings
        css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
            encoding='utf-8')
        start = css.index(chr(10) + selector + ' {') + 1
        return css[start:css.index('}', start)]

    def test_the_portrait_column_is_the_wider_one(self):
        """شش کارت سوابق از ستون چپ رفتند؛ عکس باید جای بیشتری بگیرد."""
        rule = self._rule('.pres-split')
        line = [ln for ln in rule.splitlines()
                if 'grid-template-columns' in ln][0]
        left, right = line.split('minmax(0, ')[1:]
        left_fr = int(left.split('fr')[0])
        right_fr = int(right.split('fr')[0])
        self.assertGreater(right_fr, left_fr,
                           'ستون عکس باریک‌تر از ستون رزومه است')

    def test_the_emblem_has_a_line_below_it(self):
        rule = self._rule('.pres-wcu')
        self.assertIn('margin-block-end', rule)

    def test_the_emblem_is_still_capped(self):
        """بزرگ‌کردن نباید سقف ارتفاع را بردارد."""
        rule = self._rule('.pres-wcu')
        self.assertIn('max-block-size', rule)
        self.assertIn('object-fit: contain', rule)


class PresidencyBreathingRoomTests(TestCase):
    """موسسه خواست عکس کمی کوتاه‌تر شود و دو لینک پایین‌تر بیایند."""

    def _rule(self, selector):
        return _rule(_css_text(), selector)

    def test_the_portrait_frame_is_capped(self):
        """کوتاه‌کردن از راه عرض قاب است، نه برشِ عکس."""
        rule = self._rule('.pres-portrait')
        self.assertIn('max-inline-size', rule)

    def test_the_portrait_stays_centred_in_its_column(self):
        rule = self._rule('.pres-portrait')
        self.assertIn('margin: 0 auto', rule)

    def test_the_photo_itself_is_never_cropped(self):
        rule = self._rule('.pres-portrait img')
        self.assertIn('block-size: auto', rule)
        self.assertNotIn('object-fit: cover', rule)

    def test_the_website_link_sits_lower(self):
        rule = self._rule('.wcu-link')
        self.assertIn('margin-block-start', rule)

    def test_the_resume_button_sits_lower(self):
        """دو سطر فاصلهٔ بیشتر یعنی دست‌کم ۶۰ پیکسل از لوح بالا."""
        rule = self._rule('.pres-cv-download')
        floor = int(re.search(r'margin-block-start: clamp\((\d+)px',
                              rule).group(1))
        self.assertGreaterEqual(floor, 60)
