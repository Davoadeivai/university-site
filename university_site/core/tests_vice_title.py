"""نام معاونت‌ها باید از پنل قابل ویرایش باشد.

عنوان تا امروز فقط در دو فهرست ثابتِ کد بود — یکی در مدل و یکی در
`core.vices` — و موسسه هیچ کادری برای عوض‌کردنش نداشت.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import VicePresidency, ViceUnit
from core.vices import VICE_ORDER, build


class ViceTitleTests(TestCase):

    def setUp(self):
        cache.clear()
        self.vice = VicePresidency.objects.create(
            vice_type='education', full_name='دکتر نمونه', is_active=True)

    def _rows(self):
        return {row['key']: row for row in build()}

    def test_an_empty_title_keeps_the_default_menu_label(self):
        label = dict((k, l) for k, l, _ in VICE_ORDER)['education']
        self.assertEqual(self._rows()['education']['label'], label)

    def test_a_typed_title_wins_in_the_menu(self):
        self.vice.title = 'معاونت آموزش و تحصیلات تکمیلی'
        self.vice.save()
        self.assertEqual(self._rows()['education']['label'],
                         'معاونت آموزش و تحصیلات تکمیلی')

    def test_whitespace_alone_is_not_a_title(self):
        self.vice.title = '   '
        self.vice.save()
        label = dict((k, l) for k, l, _ in VICE_ORDER)['education']
        self.assertEqual(self._rows()['education']['label'], label)

    def test_the_menu_shows_it(self):
        self.vice.title = 'معاونت آموزشِ تازه'
        self.vice.save()
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('معاونت آموزشِ تازه', html)

    def test_the_detail_page_shows_it(self):
        self.vice.title = 'معاونت آموزشِ تازه'
        self.vice.save()
        html = self.client.get(
            reverse('core:vice_detail', args=['education'])).content.decode()
        self.assertIn('معاونت آموزشِ تازه', html)

    def test_the_detail_page_falls_back_to_the_default(self):
        html = self.client.get(
            reverse('core:vice_detail', args=['education'])).content.decode()
        self.assertIn('معاونت آموزشی و تحصیلات تکمیلی', html)

    def test_display_name_falls_back(self):
        self.assertEqual(self.vice.display_name,
                         'معاونت آموزشی و تحصیلات تکمیلی')
        self.vice.title = 'الف'
        self.assertEqual(self.vice.display_name, 'الف')

    def test_a_unit_names_its_parent_by_the_typed_title(self):
        self.vice.title = 'معاونت آموزشِ تازه'
        self.vice.save()
        unit = ViceUnit.objects.create(vice=self.vice, name='ادارهٔ امتحانات')
        self.assertIn('معاونت آموزشِ تازه', str(unit))


class ViceTitleIsEditableInAdminTests(TestCase):
    """کادر باید واقعاً در فرم باشد، نه فقط در مدل."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modirvice', 'v@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)
        self.vice = VicePresidency.objects.create(
            vice_type='research', is_active=True)

    def test_the_change_form_has_the_field(self):
        html = self.client.get(
            '/admin/core/vicepresidency/%d/change/' % self.vice.pk
        ).content.decode()
        self.assertIn('name="title"', html)

    def test_it_is_editable_straight_from_the_list(self):
        from core.admin import VicePresidencyAdmin

        self.assertIn('title', VicePresidencyAdmin.list_editable)
        html = self.client.get(
            '/admin/core/vicepresidency/').content.decode()
        self.assertIn('title', html)

    def test_saving_a_title_changes_the_site(self):
        self.vice.title = 'معاونت پژوهش و فناوری'
        self.vice.save()
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('معاونت پژوهش و فناوری', html)
