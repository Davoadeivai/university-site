"""باکس رشته‌های پذیرش، نشان نوار بالا، و ترتیب گروه‌ها."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings, Slider


class AdmissionPosterBoxTests(TestCase):
    """داوطلبی که تا میانهٔ صفحه آمده، دنبال یک چیز است: رشته‌ها."""

    def setUp(self):
        cache.clear()
        self.settings_row = SiteSettings.objects.create(
            university_name_fa='موسسه', admission_poster='site/admission/p.jpg')
        # باکس، مقاطع را از رشته‌های فعال می‌سازد
        from academics.models import Department, Major

        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-admit', order=1,
            is_active=True)
        Major.objects.create(
            department=faculty, name='مهندسی نمونه', slug='nemoone-major',
            degree='bachelor_cont', is_active=True)

    def _html(self):
        return self.client.get(reverse('core:home')).content.decode()

    def test_each_degree_leads_into_the_wizard(self):
        """پیش از این باکس فقط پوستر را باز می‌کرد و راهی به جلو نبود."""
        html = self._html()
        block = html.split('admit-degrees')[1].split('</div>')[0]
        self.assertIn('کارشناسی پیوسته', block)
        self.assertIn(
            reverse('core:student_path') + '?degree=bachelor_cont&amp;step=1',
            block)

    def test_the_count_comes_from_the_database(self):
        block = self._html().split('admit-degrees')[1].split('</div>')[0]
        self.assertIn('۱ رشته', block)

    def test_the_box_is_shown(self):
        html = self._html()
        self.assertIn('admit-panel', html)
        self.assertIn('رشته‌های پذیرش دانشجو', html)

    def test_it_opens_the_poster_full_screen(self):
        box = self._html().split('admit-poster')[1].split('>')[0]
        self.assertIn('data-zoomable', box)
        self.assertIn('p.jpg', box)

    def test_it_sits_between_the_figures_and_the_calendar(self):
        html = self._html()
        stats = html.index('stats-bar')
        box = html.index('admit-panel')
        calendar = html.index('تقویم آموزشی')
        self.assertLess(stats, box)
        self.assertLess(box, calendar)

    def test_no_poster_leaves_the_degrees_behind(self):
        """پوستر که نباشد، راه ورود به انتخاب رشته باید بماند."""
        self.settings_row.admission_poster = ''
        self.settings_row.save(update_fields=['admission_poster'])
        cache.clear()
        html = self._html()
        self.assertNotIn('admit-poster', html)
        self.assertIn('admit-panel', html)

    def test_the_poster_button_is_a_button_so_the_keyboard_reaches_it(self):
        self.assertIn('<button type="button" class="admit-poster"',
                      self._html())

    def test_the_viewer_accepts_a_plain_url(self):
        """نمایشگر تا امروز فقط روی خودِ تصویر کار می‌کرد."""
        js = (Path(settings.BASE_DIR) / 'static' / 'js' / 'main.js').read_text(
            encoding='utf-8')
        self.assertIn("target.getAttribute('data-zoomable')", js)

    def test_the_panel_offers_the_upload(self):
        from core.admin import SiteSettingsAdmin

        self.assertIn('admission_poster', str(SiteSettingsAdmin.fieldsets))


class SlideButtonRemovedTests(TestCase):
    """دکمه از اسلاید برداشته شد؛ جایش باکس صفحهٔ اصلی است."""

    def setUp(self):
        cache.clear()
        for index in range(3):
            Slider.objects.create(
                title='', order=index, is_active=True,
                image='sliders/s%d.jpg' % index)

    def test_no_slide_carries_a_button(self):
        html = self.client.get(reverse('core:home')).content.decode()
        hero = html.split('id="heroTrack"')[1].split('/track')[0]
        self.assertNotIn('slide-cta', hero)

    def test_the_command_can_still_put_one_back(self):
        """برداشتن نباید یعنی از دست دادن قابلیت."""
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('set_slide_cta', stdout=out)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('slide-cta', html)


class TopbarEmblemTests(TestCase):
    """نشان کلاس جهانی، میان نشانی پشتیبانی و کلید زبان."""

    def setUp(self):
        cache.clear()
        self.settings_row = SiteSettings.objects.create(
            university_name_fa='موسسه', email='support@portal.aab.ac.ir',
            world_class_logo='site/wcu.jpg')

    def _bar(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[0]

    def test_the_emblem_is_there(self):
        self.assertIn('topbar-wcu', self._bar())

    def test_it_sits_between_the_support_address_and_the_language_key(self):
        bar = self._bar()
        support = bar.index('support@portal.aab.ac.ir')
        emblem = bar.index('topbar-wcu')
        language = bar.index('lang-switch')
        self.assertLess(support, emblem)
        self.assertLess(emblem, language)

    def test_it_leads_to_the_world_class_site(self):
        link = self._bar().split('topbar-wcu')[1].split('>')[0]
        self.assertIn('WCM-Society', link)

    def test_it_opens_in_a_new_tab_without_handing_over_ours(self):
        """بدون noopener، صفحهٔ مقصد می‌تواند به تب ما دست بزند."""
        link = self._bar().split('topbar-wcu')[1].split('>')[0]
        self.assertIn('target="_blank"', link)
        self.assertIn('noopener', link)

    def test_the_address_is_editable_from_the_panel(self):
        self.settings_row.world_class_url = 'https://example.org/wcu'
        self.settings_row.save(update_fields=['world_class_url'])
        cache.clear()
        self.assertIn('https://example.org/wcu', self._bar())

    def test_no_logo_means_no_empty_frame(self):
        self.settings_row.world_class_logo = ''
        self.settings_row.save(update_fields=['world_class_logo'])
        cache.clear()
        self.assertNotIn('topbar-wcu', self._bar())
