"""سه ایراد که هر سه یک ریشه داشتند: دو منبع برای یک چیز."""
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Announcement
from core.models import BoardMember, SiteSettings
from directory.models import DirectoryPerson


class TheBoardsHaveOneSourceTests(TestCase):
    """ویرایش «عضو هیات» انجام می‌شد و روی سایت دیده نمی‌شد.

    منو به صفحه‌ای می‌رفت که از «افراد موسسه» ساخته می‌شد، و پنل
    فهرست دیگری را ویرایش می‌کرد.
    """

    def setUp(self):
        cache.clear()
        BoardMember.objects.create(
            board_type='trustee', full_name='دکتر امینِ آزمون',
            title='رئیس هیئت امنا', is_active=True)
        BoardMember.objects.create(
            board_type='founder', full_name='مهندس مؤسسِ آزمون',
            is_active=True)
        # همان آدم در فهرست دیگر، با نامی متفاوت
        DirectoryPerson.objects.create(
            category='trustee', full_name='نامِ قدیمیِ نادرست',
            is_active=True)

    def test_the_menu_points_at_the_page_the_panel_edits(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn(reverse('core:board_trustees'), html)
        self.assertIn(reverse('core:board_founders'), html)

    def test_an_edit_in_the_panel_shows_on_the_site(self):
        html = self.client.get(
            reverse('core:board_trustees')).content.decode()
        self.assertIn('دکتر امینِ آزمون', html)

    def test_the_rival_list_no_longer_makes_a_page(self):
        html = self.client.get(
            reverse('core:board_trustees')).content.decode()
        self.assertNotIn('نامِ قدیمیِ نادرست', html)

    def test_the_founders_page_reads_the_same_source(self):
        html = self.client.get(
            reverse('core:board_founders')).content.decode()
        self.assertIn('مهندس مؤسسِ آزمون', html)

    def test_an_old_bookmark_still_lands_somewhere_right(self):
        response = self.client.get(
            reverse('directory:people_section', args=['هیات-امنا']))
        self.assertEqual(response.status_code, 301)
        self.assertIn(reverse('core:board_trustees'), response['Location'])

    def test_the_people_index_no_longer_offers_the_two_boards(self):
        from directory.views import PEOPLE_SECTIONS

        slugs = [row[0] for row in PEOPLE_SECTIONS]
        self.assertNotIn('هیات-موسس', slugs)
        self.assertNotIn('هیات-امنا', slugs)

    def test_the_other_three_sections_survive(self):
        from directory.views import PEOPLE_SECTIONS

        slugs = [row[0] for row in PEOPLE_SECTIONS]
        self.assertEqual(slugs, ['هیات-علمی', 'مدیران-گروه', 'مدرسین'])

    def test_those_three_pages_still_open(self):
        DirectoryPerson.objects.create(
            category='faculty', full_name='استادِ آزمون', is_active=True)
        response = self.client.get(
            reverse('directory:people_section', args=['هیات-علمی']))
        self.assertEqual(response.status_code, 200)


class AnUrgentNoticeCanBeClickedTests(TestCase):
    """«انتخاب واحد شروع شد» را می‌خواندی و باید خودت دنبالش می‌گشتی."""

    def setUp(self):
        cache.clear()

    def _announce(self, **kwargs):
        kwargs.setdefault('title', 'انتخاب واحد نیم‌سال آینده آغاز شد')
        kwargs.setdefault('content', '…')
        kwargs.setdefault('is_active', True)
        kwargs.setdefault('is_urgent', True)
        kwargs.setdefault('expires_at',
                          timezone.now().date() + timedelta(days=30))
        Announcement.objects.all().delete()
        return Announcement.objects.create(**kwargs)

    def _ticker(self):
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('urgent-ticker')[1].split('</div>')[0]

    def test_a_notice_with_a_target_becomes_a_link(self):
        self._announce(link='/dashboard/registration/')
        ticker = self._ticker()
        self.assertIn('<a class="urgent-item is-link"', ticker)
        self.assertIn('href="/dashboard/registration/"', ticker)

    def test_the_headline_is_what_you_click(self):
        self._announce(link='/dashboard/registration/')
        ticker = self._ticker()
        self.assertIn('انتخاب واحد نیم‌سال آینده آغاز شد', ticker)

    def test_a_notice_without_a_target_is_not_a_dead_link(self):
        self._announce(link='')
        ticker = self._ticker()
        self.assertIn('<span class="urgent-item"', ticker)
        self.assertNotIn('<a class="urgent-item', ticker)

    def test_the_panel_offers_the_field(self):
        from accounts.admin import AnnouncementAdmin

        self.assertIn('link', str(AnnouncementAdmin.fieldsets))

    def test_a_link_looks_clickable(self):
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        self.assertIn('.urgent-item.is-link', css)


class TheEmblemScaleActuallyWorksTests(TestCase):
    """‎calc(94px * 120%)‎ نامعتبر است و مرورگر بی‌صدا دورش می‌ریزد."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.all().delete()

    def test_the_ratio_is_unitless(self):
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          state_emblem_scale=120)
        self.assertEqual(row.emblem_scale_ratio, '1.20')

    def test_the_default_is_one(self):
        row = SiteSettings.objects.create(university_name_fa='موسسه')
        self.assertEqual(row.emblem_scale_ratio, '1.00')

    def test_no_percent_sign_reaches_the_page(self):
        SiteSettings.objects.create(university_name_fa='موسسه',
                                    state_emblem_scale=130)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        style = html.split('--emblem-scale: ')[1].split(';')[0]
        self.assertEqual(style, '1.30')
        self.assertNotIn('%', style)

    def test_the_stylesheet_multiplies_by_a_number(self):
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        start = css.index('.bnr-state img.bnr-emblem {')
        rule = css[start:css.index('}', start)]
        self.assertIn('var(--emblem-scale, 1)', rule)
        self.assertNotIn('100%', rule)

    def test_a_colour_emblem_keeps_its_colour(self):
        """فیلترِ برنزی رنگ را می‌خورد؛ فقط برای نشانِ سفیدِ پیش‌فرض است."""
        row = SiteSettings.objects.create(university_name_fa='موسسه',
                                          state_emblem='site/emblem/a.png')
        self.assertFalse(row.emblem_is_bronzed)

    def test_the_built_in_emblem_is_still_bronzed(self):
        row = SiteSettings.objects.create(university_name_fa='موسسه')
        self.assertTrue(row.emblem_is_bronzed)

    def test_the_panel_can_force_either_way(self):
        row = SiteSettings.objects.create(
            university_name_fa='موسسه', state_emblem='site/emblem/a.png',
            state_emblem_style='bronze')
        self.assertTrue(row.emblem_is_bronzed)
        row.state_emblem_style = 'original'
        self.assertFalse(row.emblem_is_bronzed)


class UploadingAnEmblemKeepsOtherSettingsTests(TestCase):
    """آپلود ارم، فایل فیلدهای دیگر را پاک می‌کرد."""

    def test_the_emblem_has_its_own_folder(self):
        field = SiteSettings._meta.get_field('state_emblem')
        self.assertEqual(field.upload_to, 'site/emblem/')

    def test_it_no_longer_shares_with_the_logo(self):
        for name in ('logo', 'favicon', 'world_class_logo'):
            other = SiteSettings._meta.get_field(name).upload_to
            self.assertNotEqual(
                SiteSettings._meta.get_field('state_emblem').upload_to, other)

    def test_writing_never_deletes_a_file_it_does_not_own(self):
        from pathlib import Path

        from django.conf import settings

        source = (Path(settings.BASE_DIR) / 'core' / 'imaging.py').read_text(
            encoding='utf-8')
        self.assertIn('if target == previous and storage.exists(target)',
                      source)
