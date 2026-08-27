"""تعداد پرس‌وجوی صفحه‌ها — تا N+1 دوباره برنگردد."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major
from news.models import Category, News


class NewsListQueryTests(TestCase):
    """قالب برای هر خبر یک پرس‌وجوی جدا برای دسته‌بندی می‌زد."""

    @classmethod
    def setUpTestData(cls):
        for index in range(3):
            category = Category.objects.create(
                name='دسته %d' % index, slug='c%d' % index)
            for step in range(6):
                News.objects.create(
                    title='خبر %d-%d' % (index, step),
                    slug='n%d-%d' % (index, step),
                    content='متن', category=category, is_published=True,
                    is_featured=step == 0)

    def setUp(self):
        cache.clear()

    def test_the_page_opens(self):
        self.assertEqual(
            self.client.get(reverse('news:list')).status_code, 200)

    def test_more_news_does_not_mean_more_queries(self):
        """نشانهٔ قطعی N+1: افزودن خبر، کوئری اضافه کند.

        دو شمارش با هم مقایسه می‌شوند، نه با عددی ثابت: بخشی از
        context سراسری کش می‌شود، پس عدد مطلق به گرم بودن کش بستگی
        دارد و شکننده است. آنچه معنا دارد این است که با ده برابر
        شدن خبرها، عدد تکان نخورد.
        """
        before = self._count()

        category = Category.objects.first()
        for step in range(10):
            News.objects.create(
                title='خبر تازه %d' % step, slug='extra-%d' % step,
                content='متن', category=category, is_published=True)

        self.assertEqual(self._count(), before)

    def _count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse('news:list'))
        return len(ctx)

    def test_every_category_name_is_rendered(self):
        """کم‌کردن کوئری نباید محتوا را کم کند."""
        html = self.client.get(reverse('news:list')).content.decode()
        for index in range(3):
            self.assertIn('دسته %d' % index, html)


class NewsCounterTests(TestCase):
    """دو بازدید همزمان، یکی از شمارش‌ها را گم می‌کرد."""

    def setUp(self):
        cache.clear()
        self.category = Category.objects.create(name='دسته', slug='c')
        self.article = News.objects.create(
            title='خبر', slug='khabar', content='متن',
            category=self.category, is_published=True, views_count=5)

    def test_a_visit_counts(self):
        self.client.get(self.article.get_absolute_url())
        self.article.refresh_from_db()
        self.assertEqual(self.article.views_count, 6)

    def test_the_page_shows_the_new_number(self):
        """اگر فقط دیتابیس بالا برود، بازدیدکننده عدد قدیمی می‌بیند."""
        html = self.client.get(
            self.article.get_absolute_url()).content.decode()
        self.assertNotIn('>5<', html.split('views')[0][-200:])

    def test_the_counter_does_not_overwrite_a_concurrent_visit(self):
        """با read-modify-write، بازدید همزمان گم می‌شد."""
        News.objects.filter(pk=self.article.pk).update(views_count=99)
        self.client.get(self.article.get_absolute_url())
        self.article.refresh_from_db()
        self.assertEqual(self.article.views_count, 100)

    def test_the_rest_of_the_row_is_not_rewritten(self):
        """update فقط شمارنده را می‌نویسد، نه کل ردیف."""
        News.objects.filter(pk=self.article.pk).update(title='عنوان دیگر')
        self.client.get(self.article.get_absolute_url())
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'عنوان دیگر')


class HomeFacultyCardQueryTests(TestCase):
    """هر کارت دانشکده چهار بار به دیتابیس می‌زد."""

    @classmethod
    def setUpTestData(cls):
        for index in range(3):
            faculty = Department.objects.create(
                name='دانشکده %d' % index, slug='d%d' % index,
                order=index, is_active=True)
            for step in range(3):
                group = AcademicGroup.objects.create(
                    name='گروه %d-%d' % (index, step),
                    slug='g%d-%d' % (index, step),
                    department=faculty, order=step, is_active=True)
                Major.objects.create(
                    name='رشته %d-%d' % (index, step),
                    slug='m%d-%d' % (index, step), degree='bachelor_cont',
                    department=faculty, group=group, is_active=True)

    def setUp(self):
        cache.clear()

    def _count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse('core:home'))
        return len(ctx)

    def test_another_faculty_does_not_cost_more_queries(self):
        before = self._count()
        faculty = Department.objects.create(
            name='دانشکده تازه', slug='new', order=9, is_active=True)
        AcademicGroup.objects.create(
            name='گروه تازه', slug='gn', department=faculty, is_active=True)
        self.assertEqual(self._count(), before)

    def test_the_counts_are_still_right(self):
        html = self.client.get(reverse('core:home')).content.decode()
        block = html.split('fac-grid')[1].split('</section>')[0]
        self.assertIn('3 گروه آموزشی', block)
        self.assertIn('3 رشته', block)

    def test_the_group_names_are_still_listed(self):
        html = self.client.get(reverse('core:home')).content.decode()
        block = html.split('fac-grid')[1].split('</section>')[0]
        self.assertIn('گروه 0-0', block)

    def test_an_inactive_group_is_not_counted(self):
        AcademicGroup.objects.filter(slug='g0-0').update(is_active=False)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        block = html.split('fac-grid')[1].split('</section>')[0]
        self.assertIn('2 گروه آموزشی', block)
        self.assertNotIn('گروه 0-0', block)

    def test_an_inactive_major_is_not_counted(self):
        Major.objects.filter(slug='m0-0').update(is_active=False)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        block = html.split('fac-grid')[1].split('</section>')[0]
        self.assertIn('2 رشته', block)

    def test_a_faculty_without_groups_does_not_break_the_card(self):
        Department.objects.create(
            name='دانشکده خالی', slug='empty', order=8, is_active=True)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('دانشکده خالی', html)
        self.assertEqual(
            self.client.get(reverse('core:home')).status_code, 200)
