"""نوار بالای سایت — معاونین منوی خودشان را دارند.

فهرست معاونت‌ها عمداً ثابت است و از دیتابیس نمی‌آید: سند اصلاحات
موسسه هم ترتیب مشخصی خواسته (آموزشی، پژوهشی، اداری و مالی،
دانشجویی، فنی و عمرانی) و هم زیرمجموعهٔ متفاوتی برای هرکدام —
دو چیزی که یک حلقهٔ ساده روی رکوردها نمی‌تواند بسازد.
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import VicePresidency


class DeputiesMenuTests(TestCase):
    """هفت معاونت زیر منوی «حوزه ریاست» گم می‌شدند."""

    @classmethod
    def setUpTestData(cls):
        VicePresidency.objects.create(
            vice_type='education', full_name='دکتر محمدعلی جعفری',
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
        self.assertIn('معاونین', nav)
        self.assertIn(reverse('core:vices_list'), nav)

    def test_deputies_left_the_presidency_menu(self):
        nav = self._nav()
        presidency = nav.split('معاونین')[0]
        self.assertNotIn(reverse('core:vice_detail', args=['education']),
                         presidency,
                         'معاونت هنوز داخل منوی حوزه ریاست است')

    def test_each_deputy_is_listed_once(self):
        nav = self._nav()
        for vice_type in ('education', 'research', 'admin_finance',
                          'student', 'construction'):
            url = reverse('core:vice_detail', args=[vice_type])
            self.assertEqual(nav.count('href="%s"' % url), 1,
                             '%s یک بار در نوار نیست' % vice_type)

    def test_presidency_menu_keeps_its_own_items(self):
        nav = self._nav()
        self.assertIn(reverse('core:presidency'), nav)
        self.assertIn(reverse('core:presidency_office'), nav)
        self.assertIn(reverse('core:security_office'), nav)

    def test_the_menu_survives_an_empty_database(self):
        """فهرست ثابت است، پس نبودِ رکورد نباید منو را خالی کند.

        نسخهٔ قبلی از دیتابیس می‌خواند و اینجا پیام «معاونتی ثبت
        نشده» می‌داد؛ حالا پنج معاونت همیشه در منو هستند و صفحهٔ
        هرکدام خودش می‌گوید اطلاعاتش پر نشده.
        """
        VicePresidency.objects.all().delete()
        cache.clear()
        nav = self._nav()
        self.assertIn('۱. معاونت آموزشی', nav)
        self.assertIn('۵. معاونت فنی و عمرانی', nav)
