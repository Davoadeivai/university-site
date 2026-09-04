"""صفحهٔ اصلی و صفحهٔ معرفی — تغییرهای این دور."""
from pathlib import Path

from django.conf import settings as django_settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import Department, Major
from core.models import SiteSettings
from faculty.models import Professor


def _css():
    return (Path(django_settings.BASE_DIR) / 'static' / 'css' /
            'main.css').read_text(encoding='utf-8')


class FacultyStripIsGoneTests(TestCase):
    """«هیئت علمی برگزیده» به درخواست موسسه از صفحهٔ اصلی رفت."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')
        Professor.objects.create(
            first_name='نمونه', last_name='استاد', rank='assistant',
            is_active=True, is_featured=True)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_strip_is_not_on_the_home_page(self):
        html = self._html()
        self.assertNotIn('هیئت علمی برگزیده', html)
        self.assertNotIn('prof-card', html)

    def test_the_faculty_page_still_works(self):
        self.assertEqual(
            self.client.get(reverse('faculty:list')).status_code, 200)


class AdmissionBoxLeadsSomewhereTests(TestCase):
    """باکس پذیرش، بن‌بست بود: پوستر باز می‌شد و تمام."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-showcase', order=1,
            is_active=True)
        Major.objects.create(
            department=faculty, name='حسابداری', slug='hesab-showcase',
            degree='master', is_active=True)
        Major.objects.create(
            department=faculty, name='مهندسی برق', slug='bargh-showcase',
            degree='bachelor_cont', is_active=True)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_every_degree_with_a_major_gets_a_door(self):
        block = self._html().split('admit-degrees')[1].split('admit-foot')[0]
        self.assertIn('کارشناسی ارشد', block)
        self.assertIn('کارشناسی پیوسته', block)

    def test_a_degree_without_majors_is_not_offered(self):
        block = self._html().split('admit-degrees')[1].split('admit-foot')[0]
        self.assertNotIn('کاردانی فنی', block)

    def test_the_wizard_is_one_click_away(self):
        html = self._html()
        self.assertIn(reverse('core:student_path'), html)
        self.assertIn('شروع مسیر پذیرش و انتخاب رشته', html)

    def test_the_door_opens_on_the_major_step(self):
        block = self._html().split('admit-degrees')[1].split('admit-foot')[0]
        self.assertIn('step=1', block)
        self.assertIn('degree=master', block)

    def test_that_link_actually_resolves(self):
        url = reverse('core:student_path') + '?degree=master&step=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('حسابداری', response.content.decode())


class AboutPageTests(TestCase):
    """معرفی موسسه: رتبه بدون «ممتاز»، و یک عکس واقعی."""

    def setUp(self):
        cache.clear()
        self.settings_row = SiteSettings.objects.create(
            university_name_fa='موسسه', established_year='۱۳۷۰')

    def _html(self):
        return self.client.get(reverse('core:about')).content.decode()

    def test_the_rank_card_no_longer_says_momtaz(self):
        html = self._html()
        self.assertIn('رتبه عالی', html)
        self.assertNotIn('>ممتاز<', html)

    def test_the_side_box_shows_a_photograph(self):
        """پیش از این یک آیکون روی مستطیل رنگی بود."""
        html = self._html()
        self.assertIn('about-shot', html)
        self.assertIn('hero-campus-01', html)

    def test_the_admin_can_replace_that_photograph(self):
        self.settings_row.about_image = 'site/about/campus.jpg'
        self.settings_row.save(update_fields=['about_image'])
        cache.clear()
        html = self._html()
        self.assertIn('site/about/campus.jpg', html)
        self.assertNotIn('hero-campus-01.jpg" ', html)

    def test_the_panel_offers_the_upload(self):
        from core.admin import SiteSettingsAdmin

        self.assertIn('about_image', str(SiteSettingsAdmin.fieldsets))

    def test_the_chart_is_not_blown_up_past_its_own_size(self):
        """کشیدن تصویر روی قاب پهن، خطوط چارت را مات می‌کرد."""
        template = (Path(django_settings.BASE_DIR) / 'templates' / 'core' /
                    'about.html').read_text(encoding='utf-8')
        self.assertIn('max-inline-size: {{ settings.org_chart_size.0 }}px',
                      template)

    def test_the_chart_filter_is_gentle(self):
        rule = _css().split('.org-chart-img {')[1].split('}')[0]
        self.assertIn('contrast(1.06)', rule)


class FooterTests(TestCase):
    """فوتر باید همان ساختاری را نشان دهد که سایت امروز دارد."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه علامه امینی')

    def _footer(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('<footer class="main-footer">')[1]

    def test_it_carries_the_institute_mark_not_a_generic_icon(self):
        footer = self._footer()
        self.assertIn('footer-logo-mark', footer)

    def test_the_education_column_matches_the_menu(self):
        footer = self._footer()
        for url in (reverse('academics:departments'),
                    reverse('academics:majors'),
                    reverse('academics:groups_list'),
                    reverse('academics:group_heads'),
                    reverse('core:councils')):
            self.assertIn(url, footer)

    def test_the_copyright_names_the_institute(self):
        footer = self._footer()
        self.assertIn('footer-copy', footer)
        self.assertIn('موسسه علامه امینی', footer)


class HomePolishTests(TestCase):
    """قواعد ظاهری صفحهٔ اصلی نباید به بقیهٔ صفحه‌ها نشت کند."""

    def test_the_polish_is_scoped_to_the_home_page(self):
        css = _css()
        block = css.split('صفحهٔ اصلی — پرداخت نهایی')[1]
        for selector in ('.section-title::after', '.stat-number',
                         '.quick-link-card:hover'):
            head = block.split(selector)[0]
            self.assertIn('.home-page', head[-400:], selector)

    def test_the_body_carries_that_hook(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('class="home-page"', html)

    def test_other_pages_do_not(self):
        html = self.client.get(reverse('core:about')).content.decode()
        self.assertNotIn('class="home-page"', html)


class SelectionAndCtaTests(TestCase):
    """آبیِ پیش‌فرضِ مرورگر، و متن سفید روی تصویر روشن."""

    def test_selected_text_is_not_browser_blue(self):
        css = _css()
        self.assertIn('::selection', css)
        rule = css.split('::selection {')[1].split('}')[0]
        self.assertIn('var(--primary', rule)

    def test_dark_bands_flip_the_selection_colours(self):
        css = _css()
        self.assertIn('.cta-band ::selection', css)
        self.assertIn('.uni-hero-wrap ::selection', css)

    def test_the_final_band_carries_its_own_scrim(self):
        """مدیر می‌تواند آسمانِ روشن زیر متن سفید بگذارد."""
        css = _css()
        rule = css.split('.cta-band::before {')[1].split('}')[0]
        self.assertIn('rgba(78, 18, 32', rule)

    def test_the_band_is_marked_in_the_template(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('section cta-band', html)


class NewsSectionTests(TestCase):
    """اخبار سمت راست، و همه‌چیز از راست."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_the_section_is_marked_for_right_alignment(self):
        self.assertIn('section-alt home-news', self._html())

    def test_the_news_column_comes_before_the_announcements(self):
        """ستون نخست در صفحهٔ راست‌چین، سمت راست می‌نشیند."""
        html = self._html()
        news = html.index('آخرین اخبار')
        announcements = html.index('اطلاعیه‌ها</h2>')
        self.assertLess(news, announcements)

    def test_the_alignment_rules_exist(self):
        css = _css()
        block = css.split('.home-news { text-align: start; }')[1]
        self.assertIn('.home-news .announce-title', block[:600])

    def test_the_headline_rule_starts_from_the_right(self):
        css = _css()
        self.assertIn('.home-news .section-title::after { margin-inline: 0; }',
                      css)


class BannerEmblemTests(TestCase):
    """نشان وزارت از لبه بریده می‌شد."""

    def test_the_emblem_column_cannot_be_squeezed(self):
        # سلکتور مشترک ‎.bnr-mark, .bnr-state‎ هم بالاتر هست
        rule = _css().split('\n.bnr-state {')[1].split('}')[0]
        self.assertIn('flex: none', rule)

    def test_the_emblem_scales_instead_of_being_cropped(self):
        rule = _css().split('\n.bnr-state img {')[1].split('}')[0]
        self.assertIn('object-fit: contain', rule)
        self.assertIn('max-inline-size: 100%', rule)

    def test_the_middle_column_cannot_crush_the_sides(self):
        rule = _css().split('.site-banner > a {')[1].split('}')[0]
        self.assertIn('minmax(0, 1fr)', rule)

    def test_the_emblem_block_never_wraps(self):
        """بنر قدِ ثابت دارد؛ خط دوم یعنی نصفِ نشان زیر برش."""
        rule = _css().split('%s.bnr-state {' % chr(10))[1].split('}')[0]
        self.assertIn('flex-wrap: nowrap', rule)

    def test_the_caption_shrinks_before_the_emblem_does(self):
        rule = _css().split('%s.bnr-min {' % chr(10))[1].split('}')[0]
        self.assertIn('min-width: 0', rule)
        self.assertIn('text-overflow: ellipsis', rule)

    def test_the_captions_step_aside_early_enough(self):
        css = _css()
        self.assertIn('@media (max-width: 1300px)', css)

    def test_the_banner_does_not_clip_its_marks(self):
        """لایه‌های تزئینی inset:0 دارند؛ برش فقط نشان‌ها را می‌برید."""
        rule = _css().split('%s.site-banner {' % chr(10))[1].split('}')[0]
        self.assertIn('overflow: visible', rule)
        self.assertNotIn('overflow: hidden', rule)

    def test_the_emblem_keeps_a_step_from_that_edge(self):
        rule = _css().split('%s.bnr-state {' % chr(10))[1].split('}')[0]
        self.assertIn('padding-inline-end', rule)

    def test_the_marks_do_not_drift_sideways(self):
        """پارالاکسِ افقی، نشانِ کنارِ لبه را از قاب بیرون می‌برد."""
        rule = _css().split('.bnr-mark, .bnr-state { transform:')[1]             .split(';')[0]
        self.assertIn('translate3d(0,', rule)

    def test_the_emblem_is_gold_on_the_night_banner(self):
        rule = _css().split('[data-theme="dark"] .bnr-state img {')[1]             .split('}')[0]
        self.assertIn('invert(84%)', rule)
