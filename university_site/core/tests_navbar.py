"""نوار بالای سایت — معاونت‌ها منوی خودشان را دارند."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import VicePresidency


class DeputiesMenuTests(TestCase):
    """هفت معاونت زیر منوی «حوزه ریاست» گم می‌شدند."""

    @classmethod
    def setUpTestData(cls):
        VicePresidency.objects.create(
            vice_type='educational', full_name='دکتر محمدعلی جعفری',
            is_active=True)
        VicePresidency.objects.create(
            vice_type='research', full_name='دکتر حسن عمرانی',
            is_active=True)

    def setUp(self):
        # context_processor فهرست معاونت‌ها را ۶۰ ثانیه کش می‌کند؛
        # بدون پاک‌کردن، هر تست نتیجهٔ تست قبلی را می‌بیند.
        cache.clear()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('<!-- حوزه ریاست -->')[1].split('گروه های آموزشی')[0]

    def test_a_deputies_menu_exists(self):
        nav = self._nav()
        self.assertIn('معاونت‌ها', nav)
        self.assertIn(reverse('core:vices_list'), nav)

    def test_deputies_left_the_presidency_menu(self):
        """هر معاونت باید یک بار در نوار باشد، نه دو بار."""
        nav = self._nav()
        presidency = nav.split('معاونت‌ها')[0]
        self.assertNotIn(reverse('core:vice_detail', args=['educational']),
                         presidency,
                         'معاونت هنوز داخل منوی حوزه ریاست است')

    def test_each_active_deputy_is_listed_once(self):
        nav = self._nav()
        for vice_type in ('educational', 'research'):
            url = reverse('core:vice_detail', args=[vice_type])
            self.assertEqual(nav.count('href="%s"' % url), 1,
                             '%s یک بار در نوار نیست' % vice_type)

    def test_presidency_menu_keeps_its_own_items(self):
        nav = self._nav()
        self.assertIn(reverse('core:presidency'), nav)
        self.assertIn(reverse('core:presidency_office'), nav)
        self.assertIn(reverse('core:security_office'), nav)

    def test_empty_list_says_so_instead_of_a_blank_menu(self):
        VicePresidency.objects.all().delete()
        self.assertIn('معاونتی ثبت نشده', self._nav())
