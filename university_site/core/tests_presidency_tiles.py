"""رنگ کارت‌های ارتباط، فاصلهٔ عکس، و طبقهٔ سوم در هر دو جا."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import PresidencyOffice


class PresidencyTileColourTests(TestCase):
    """مدیر باید رنگ پنج کارت پایین صفحهٔ ریاست را از پنل عوض کند."""

    @classmethod
    def setUpTestData(cls):
        cls.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_phone='02133334444',
            president_email='ri@aab.ac.ir',
            office_hours='شنبه تا پنج‌شنبه',
            office_floor='طبقهٔ سوم',
            office_address='تهران، ساختمان مرکزی، طبقهٔ سوم، دفتر ریاست',
        )

    def setUp(self):
        cache.clear()

    def _html(self):
        return self.client.get(reverse('core:presidency')).content.decode()

    def _tile(self, number):
        html = self._html()
        return html.split('pres-tile-%d' % number)[1].split('>')[0]

    def test_no_colour_leaves_the_default_in_place(self):
        """کارت بی‌رنگ نباید صفت style خالی بگیرد."""
        self.assertNotIn('style=""', self._html())

    def test_a_colour_reaches_its_own_card(self):
        self.office.tile_color_phone = '#1f5c4a'
        self.office.save(update_fields=['tile_color_phone'])
        cache.clear()
        self.assertIn('--tile:#1f5c4a', self._tile(1))

    def test_each_card_has_its_own_colour(self):
        self.office.tile_color_phone = '#111111'
        self.office.tile_color_address = '#222222'
        self.office.save(update_fields=['tile_color_phone', 'tile_color_address'])
        cache.clear()
        self.assertIn('--tile:#111111', self._tile(1))
        self.assertIn('--tile:#222222', self._tile(5))
        self.assertNotIn('--tile', self._tile(3))

    def test_all_five_cards_are_offered(self):
        for key in ('phone', 'email', 'hours', 'floor', 'address'):
            self.assertTrue(
                hasattr(PresidencyOffice, 'tile_color_%s' % key),
                'کارت %s رنگ‌پذیر نیست' % key)

    def test_a_short_hex_is_accepted(self):
        self.office.tile_color_hours = '#abc'
        self.office.save(update_fields=['tile_color_hours'])
        cache.clear()
        self.assertIn('--tile:#abc', self._tile(3))

    def test_anything_that_is_not_a_hex_is_thrown_away(self):
        """مقدار آزاد داخل style می‌تواند از اعلان بیرون بزند."""
        for junk in ('red; } body { display:none', 'javascript:x',
                     'url(x)', '#12', 'expression(1)'):
            self.office.tile_color_phone = junk
            self.office.save(update_fields=['tile_color_phone'])
            cache.clear()
            html = self._html()
            self.assertNotIn(junk, html, junk)
            self.assertNotIn('--tile', self._tile(1))

    def test_the_panel_offers_a_colour_picker(self):
        from core.admin import PresidencyOfficeAdmin
        names = str(PresidencyOfficeAdmin.fieldsets)
        for key in ('phone', 'email', 'hours', 'floor', 'address'):
            self.assertIn('tile_color_%s' % key, names)


class PresidencyFloorTests(TestCase):
    """موسسه خواست هر دو جا «طبقه سوم» بنویسد؛ یکی «دوم» می‌گفت."""

    def setUp(self):
        cache.clear()
        self.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            office_floor='طبقهٔ سوم',
            office_address='تهران، ساختمان مرکزی، طبقهٔ سوم، دفتر ریاست',
        )

    def test_both_places_say_the_same_floor(self):
        html = self.client.get(reverse('core:presidency')).content.decode()
        self.assertIn('طبقهٔ سوم', self.office.office_address)
        self.assertIn('طبقهٔ سوم', html)
        self.assertNotIn('طبقهٔ دوم', html)

    def test_the_seeder_aligns_a_stale_address(self):
        """اگر نشانی طبقهٔ دیگری بگوید، دستور دیپلوی باید اصلاحش کند."""
        from io import StringIO

        from django.core.management import call_command

        self.office.office_address = 'تهران، ساختمان مرکزی، طبقهٔ دوم، دفتر ریاست'
        self.office.save(update_fields=['office_address'])
        call_command('seed_president_cv', stdout=StringIO())
        self.office.refresh_from_db()
        self.assertIn('طبقهٔ سوم', self.office.office_address)
        self.assertNotIn('طبقهٔ دوم', self.office.office_address)

    def test_aligning_keeps_the_rest_of_the_address(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_president_cv', stdout=StringIO())
        self.office.refresh_from_db()
        self.assertIn('دفتر ریاست', self.office.office_address)
        self.assertIn('ساختمان مرکزی', self.office.office_address)


class PresidencyPortraitSpacingTests(TestCase):
    """میان عکس رئیس و ارم کلاس جهانی باید فاصله باشد."""

    def test_the_two_columns_are_held_apart(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
            encoding='utf-8')
        block = css.split('.pres-split')[1].split('}')[0]
        self.assertIn('gap:', block)
        # مقدار پیشین ۲۰ تا ۴۶ پیکسل بود و عکس به ارم می‌چسبید.
        self.assertIn('clamp(28px, 5vw, 76px)', block)


class WcuTitleTests(TestCase):
    """موسسه خواست «مدیریت کلاس جهانی» برداشته شود."""

    def setUp(self):
        cache.clear()
        self.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            wcu_title='سایت تخصصی کلینیک',
            wcu_motto='چگونگی تبدیل دانشگاه‌ها به سازمان در کلاس جهانی',
            president_website='https://WCM-Society.Com')

    def _html(self):
        return self.client.get(reverse('core:presidency')).content.decode()

    def test_the_new_wording_is_on_the_page(self):
        self.assertIn('سایت تخصصی کلینیک', self._html())

    def test_the_old_wording_is_gone(self):
        self.assertNotIn('سایت تخصصی مدیریت کلاس جهانی', self._html())

    def test_the_seeder_writes_the_new_wording(self):
        """اگر seeder عبارت قدیمی را نگه دارد، دیپلوی برش می‌گرداند."""
        from core.management.commands.seed_president_cv import FIELDS

        self.assertEqual(FIELDS['wcu_title'], 'سایت تخصصی کلینیک')

    def test_the_seeder_does_not_overwrite_an_edit(self):
        """مدیر باید بتواند از پنل عوضش کند بی‌آنکه دیپلوی برگرداند."""
        from io import StringIO

        from django.core.management import call_command

        self.office.wcu_title = 'عنوان دست‌نویس مدیر'
        self.office.save(update_fields=['wcu_title'])
        call_command('seed_president_cv', stdout=StringIO())
        self.office.refresh_from_db()
        self.assertEqual(self.office.wcu_title, 'عنوان دست‌نویس مدیر')

    def test_an_empty_title_does_not_leave_a_stray_heading(self):
        self.office.wcu_title = ''
        self.office.save(update_fields=['wcu_title'])
        cache.clear()
        plaque = self._html().split('wcu-plaque')[1].split('</aside>')[0]
        self.assertNotIn('wcu-title', plaque)


class PresidencyCaptionTests(TestCase):
    """سه خط زیر عکس رئیس — اندازه و رنگ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from pathlib import Path

        from django.conf import settings

        cls.css = (Path(settings.BASE_DIR) / 'static' / 'css' /
                   'main.css').read_text(encoding='utf-8')

    @staticmethod
    def _contrast(one, two):
        def luminance(value):
            value = value.lstrip('#')
            parts = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            parts = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
                     for c in parts]
            return .2126 * parts[0] + .7152 * parts[1] + .0722 * parts[2]

        first, second = luminance(one), luminance(two)
        return (max(first, second) + .05) / (min(first, second) + .05)

    def _block(self, selector):
        return self.css.split(selector + ' {')[1].split('}')[0]

    def test_the_word_riyasat_is_no_longer_a_tiny_label(self):
        """موسسه خواست درشت‌تر باشد؛ ۱۲ پیکسل ثابت بود."""
        block = self._block('.pres-eyebrow')
        self.assertIn('clamp(18px, 2vw, 25px)', block)
        self.assertNotIn('font-size: 12px', block)

    def test_each_of_the_three_lines_has_its_own_colour(self):
        colours = {self._colour('.pres-eyebrow'),
                   self._colour('.pres-name'),
                   self._colour('.pres-title')}
        self.assertEqual(len(colours), 3)

    def _colour(self, selector):
        for line in self._block(selector).splitlines():
            line = line.strip()
            if line.startswith('color:'):
                return line.split(':')[1].split(';')[0].strip()
        self.fail('%s رنگی ندارد' % selector)

    def test_all_three_stay_legible_on_the_card(self):
        """تمایز رنگی نباید به بهای خوانایی تمام شود."""
        ground = '#3a0f1a'
        for selector in ('.pres-eyebrow', '.pres-name', '.pres-title'):
            ratio = self._contrast(self._colour(selector), ground)
            self.assertGreater(ratio, 7, selector)

    def test_the_card_is_maroon_not_navy(self):
        """‎#0d2144‎ از تم قدیمی مانده بود و کنار لوح عنابی می‌زد."""
        block = self.css.split('.pres-portrait figcaption {')[1].split('}')[0]
        # فقط اعلان background سنجیده می‌شود؛ کامنت بالای آن نام رنگ
        # قدیمی را می‌برد تا معلوم باشد چه چیزی عوض شده.
        declared = next(line.strip() for line in block.splitlines()
                        if line.strip().startswith('background:'))
        self.assertNotIn('#0d2144', declared)
        self.assertIn('#4e1220', declared)

    def test_persian_letters_are_not_pulled_apart(self):
        self.assertNotIn('letter-spacing', self._block('.pres-eyebrow'))

    def test_the_caption_still_renders(self):
        cache.clear()
        PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_title='استاد گروه مدیریت صنعتی')
        html = self.client.get(reverse('core:presidency')).content.decode()
        block = html.split('<figcaption>')[1].split('</figcaption>')[0]
        self.assertIn('ریاست', block)
        self.assertIn('دکتر حسن فارسیجانی', block)
        self.assertIn('استاد گروه مدیریت صنعتی', block)
