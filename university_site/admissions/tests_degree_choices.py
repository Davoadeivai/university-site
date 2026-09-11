"""کشوی مقطع در فرم پذیرش، مقطعِ بی‌رشته پیشنهاد نکند.

متقاضی «کاردانی فنی» را انتخاب می‌کرد و کشوی «اولویت اول رشته» خالی
می‌ماند — بدون یک کلمه توضیح که چرا. سند رشته‌ها ۵۶ رشته دارد و
هیچ‌کدام کاردانی فنی نیست، ولی آن مقطع در فهرست ثابتِ قالب بود.
"""
from django.test import TestCase, override_settings
from django.urls import reverse

from academics.models import Department, Major


class OnlyDegreesWithMajorsAreOfferedTests(TestCase):

    def setUp(self):
        self.dept = Department.objects.create(
            name='دانشکدهٔ نمونه', slug='d1')

    def _make(self, slug, degree):
        return Major.objects.create(
            name='رشتهٔ %s' % slug, slug=slug,
            department=self.dept, degree=degree, is_active=True)

    def _choices(self):
        from admissions.views import _degrees_that_have_majors

        return dict(_degrees_that_have_majors(
            list(Major.objects.filter(is_active=True))))

    def test_a_degree_with_majors_is_offered(self):
        self._make('m1', 'associate_cont')
        self.assertIn('associate_cont', self._choices())

    def test_a_degree_without_majors_is_not_offered(self):
        """همان اتفاقی که برای کاردانی فنی می‌افتاد."""
        self._make('m1', 'associate_cont')
        self.assertNotIn('associate_tech', self._choices())

    def test_it_appears_as_soon_as_a_major_is_added(self):
        """اگر روزی رشتهٔ کاردانی فنی ثبت شود، خودش پیدا می‌شود."""
        self._make('m1', 'associate_tech')
        self.assertIn('associate_tech', self._choices())

    def test_an_inactive_major_does_not_count(self):
        major = self._make('m1', 'associate_tech')
        Major.objects.filter(pk=major.pk).update(is_active=False)
        self.assertNotIn('associate_tech', self._choices())

    def test_the_official_order_is_kept(self):
        """ترتیب مقاطع را سند موسسه تعیین کرده، نه ترتیب ثبت رشته."""
        self._make('m1', 'master')
        self._make('m2', 'associate_cont')
        self.assertEqual(list(self._choices()),
                         ['associate_cont', 'master'])

    def test_a_legacy_code_lands_under_its_official_degree(self):
        """رکوردهای قدیمی «کاردانی» باید زیر «کاردانی پیوسته» بیایند."""
        self._make('m1', 'associate')
        self.assertIn('associate_cont', self._choices())

    def test_no_majors_at_all_offers_nothing(self):
        self.assertEqual(self._choices(), {})


@override_settings(ADMISSION_REQUIRE_MOBILE_OTP=False)
class TheFormShowsTheRightDegreesTests(TestCase):
    """همان قاعده، این بار از دلِ صفحهٔ واقعی."""

    def setUp(self):
        dept = Department.objects.create(name='دانشکدهٔ نمونه', slug='d1')
        Major.objects.create(
            name='حسابداری', slug='hesabdari', department=dept,
            degree='associate_cont', is_active=True)

    def _form(self):
        response = self.client.get(reverse('admissions:apply'))
        return response.content.decode()

    def test_the_empty_degree_is_gone_from_the_dropdown(self):
        html = self._form()
        block = html.split('id="degree"')[1].split('</select>')[0]
        self.assertNotIn('کاردانی فنی', block)

    def test_the_degree_that_has_a_major_is_there(self):
        html = self._form()
        block = html.split('id="degree"')[1].split('</select>')[0]
        self.assertIn('کاردانی پیوسته', block)

    def test_nothing_is_offered_when_no_major_exists(self):
        """قالب یک فهرست دستیِ پنج‌تایی هم داشت.

        همان فهرست، «کاردانی فنی» را برمی‌گرداند و اشتباه را
        زنده نگه می‌داشت.
        """
        Major.objects.all().delete()
        html = self._form()
        block = html.split('id="degree"')[1].split('</select>')[0]
        for label in ('کاردانی فنی', 'کارشناسی ارشد'):
            self.assertNotIn(label, block)
        self.assertIn('هنوز رشته‌ای برای پذیرش', html)
