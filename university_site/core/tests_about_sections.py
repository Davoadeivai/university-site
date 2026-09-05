"""بخش‌های دلخواهِ صفحهٔ «معرفی دانشگاه».

صفحه پنج متنِ ثابت داشت و هیچ راهی نبود موسسه چیز تازه‌ای به آن
اضافه کند — هر خواسته یعنی یک ویرایش در قالب و یک دیپلوی.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import AboutSection, SiteSettings


class AboutSectionContentTests(TestCase):

    def test_each_line_becomes_a_card(self):
        block = AboutSection(body='کتابخانه | ۳۰٬۰۰۰ جلد\nسلف سرویس')
        self.assertEqual(block.cards, [
            {'title': 'کتابخانه', 'text': '۳۰٬۰۰۰ جلد'},
            {'title': '', 'text': 'سلف سرویس'},
        ])

    def test_blank_lines_are_dropped(self):
        block = AboutSection(body='یک\n\n\nدو')
        self.assertEqual(len(block.cards), 2)
        self.assertEqual(block.paragraphs, ['یک', 'دو'])

    def test_an_empty_body_yields_nothing(self):
        self.assertEqual(AboutSection(body='').cards, [])
        self.assertEqual(AboutSection().paragraphs, [])

    def test_only_the_first_bar_splits_a_card(self):
        block = AboutSection(body='عنوان | متن | با خط عمودی')
        self.assertEqual(block.cards[0]['text'], 'متن | با خط عمودی')


class AboutSectionsOnThePageTests(TestCase):

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:about')).content.decode()

    def test_nothing_is_added_when_no_row_exists(self):
        self.assertNotIn('<div class="about-block ', self._html())

    def test_a_section_reaches_the_page(self):
        AboutSection.objects.create(
            title='امکانات آموزشی', body='کتابخانه', is_active=True)
        html = self._html()
        self.assertIn('امکانات آموزشی', html)
        self.assertIn('کتابخانه', html)

    def test_an_inactive_section_stays_off(self):
        AboutSection.objects.create(
            title='بخش خاموش', body='…', is_active=False)
        self.assertNotIn('بخش خاموش', self._html())

    def test_the_order_is_honoured(self):
        AboutSection.objects.create(title='دومی', order=2, is_active=True)
        AboutSection.objects.create(title='اولی', order=1, is_active=True)
        html = self._html()
        self.assertLess(html.index('اولی'), html.index('دومی'))

    def test_the_cards_layout_renders_cards(self):
        AboutSection.objects.create(
            title='امکانات', layout='cards', is_active=True,
            body='کتابخانه | ۳۰٬۰۰۰ جلد\nآزمایشگاه | مجهز')
        html = self._html()
        self.assertEqual(html.count('class="about-card"'), 2)
        self.assertIn('۳۰٬۰۰۰ جلد', html)

    def test_the_highlight_layout_renders_a_panel(self):
        AboutSection.objects.create(
            title='پیام', layout='highlight', body='یک جمله', is_active=True)
        self.assertIn('<div class="about-highlight"', self._html())

    def test_a_split_layout_without_an_image_falls_back_to_text(self):
        """چیدمان تصویردار بدون تصویر نباید یک ستون خالی بسازد."""
        AboutSection.objects.create(
            title='بی‌عکس', layout='image_end', body='متن', is_active=True)
        html = self._html()
        self.assertNotIn('<div class="about-split', html)
        self.assertIn('<div class="about-block-text"', html)

    def test_the_icon_is_shown_when_given(self):
        AboutSection.objects.create(
            title='افتخارات', icon='fas fa-award', is_active=True)
        self.assertIn('fas fa-award', self._html())

    def test_they_sit_after_the_chart(self):
        AboutSection.objects.create(title='بخش تازه', is_active=True)
        html = self._html()
        self.assertLess(html.index('چارت سازمانی'), html.index('بخش تازه'))


class AboutSectionPanelTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modirabout', 'a@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)

    def test_the_panel_offers_it(self):
        response = self.client.get('/admin/core/aboutsection/')
        self.assertEqual(response.status_code, 200)

    def test_a_section_can_be_created_there(self):
        response = self.client.post('/admin/core/aboutsection/add/', {
            'title': 'افتخارات', 'subtitle': '', 'icon': 'fas fa-award',
            'body': 'رتبهٔ عالی', 'layout': 'text', 'order': '1',
            'is_active': 'on',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AboutSection.objects.filter(title='افتخارات').exists())

    def test_the_list_can_reorder_without_opening_forms(self):
        from core.admin import AboutSectionAdmin

        for field in ('layout', 'order', 'is_active'):
            self.assertIn(field, AboutSectionAdmin.list_editable)
