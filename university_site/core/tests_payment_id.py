"""صفحهٔ شناسه واریز: جست‌وجو فقط با شماره دانشجویی."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import PaymentIdentifier


class TheSearchTakesOnlyTheStudentNumberTests(TestCase):
    """کد ملی از جست‌وجو برداشته شد — به درخواست موسسه.

    و خوب شد: هر کسی با داشتنِ کد ملیِ یک نفر می‌توانست نام و شناسهٔ
    واریزش را بیرون بکشد. شمارهٔ دانشجویی را فقط خودِ دانشجو دارد.
    """

    def setUp(self):
        cache.clear()
        self.url = reverse('core:payment_id')
        self.row = PaymentIdentifier.objects.create(
            full_name='نمونهٔ دانشجو', national_id='2050123456',
            student_number='99123456', payment_id='777000111',
            is_active=True)

    def _search(self, query):
        return self.client.post(self.url, {'query': query})

    def test_the_student_number_finds_it(self):
        self.assertContains(self._search('99123456'), '777000111')

    def test_persian_digits_find_it_too(self):
        """دانشجو با صفحه‌کلید فارسی تایپ می‌کند."""
        self.assertContains(self._search('۹۹۱۲۳۴۵۶'), '777000111')

    def test_the_national_id_no_longer_finds_it(self):
        self.assertNotContains(self._search('2050123456'), '777000111')

    def test_the_payment_id_itself_no_longer_finds_it(self):
        self.assertNotContains(self._search('777000111'), 'نمونهٔ دانشجو')

    def test_an_inactive_row_is_not_found(self):
        PaymentIdentifier.objects.update(is_active=False)
        self.assertNotContains(self._search('99123456'), '777000111')

    def test_an_unknown_number_says_nothing_was_found(self):
        response = self._search('00000000')
        self.assertNotContains(response, '777000111')
        self.assertEqual(response.status_code, 200)

    def test_the_form_asks_only_for_the_student_number(self):
        html = self.client.get(self.url).content.decode()
        block = html.split('name="query"')[0][-400:]
        self.assertNotIn('کد ملی', block)
        self.assertIn('شماره دانشجویی', html)


class TheContactCardDoesNotStretchTests(TestCase):
    """کارت «اطلاعات تماس» تا ته ستونِ فرم کش می‌آمد.

    \u200Euni-card\u200E سراسری \u200Eheight: 100%\u200E دارد تا کارت‌های یک ردیفِ شبکه
    هم‌قد شوند؛ ولی این کارت تنها در ستون خودش است و کنارِ فرمِ بلند
    می‌نشیند — شش خط اطلاعات در بالای چند صد پیکسل فضای خالی.
    """

    def test_the_card_opts_out_of_the_full_height(self):
        html = self.client.get(reverse('contact:contact')).content.decode()
        block = html.split('اطلاعات تماس')[0][-300:]
        self.assertIn('uni-card-fit', block)

    def test_the_opt_out_rule_exists(self):
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        self.assertIn('.uni-card-fit { height: auto; }', css)
