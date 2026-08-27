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
