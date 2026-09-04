"""راهنمای متنی چارت سازمانی، زیر تصویر چارت.

تصویر چارت روی موبایل خوانده نمی‌شود، با Ctrl+F پیدا نمی‌شود، و
واحدهایش کلیک نمی‌شوند. این فهرست همان ساختار را در متن می‌گذارد.
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core import org_chart
from core.models import SiteSettings


class ChartIndexDataTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_it_starts_at_the_top_of_the_chart(self):
        titles = [row['title'] for row in org_chart.build()]
        self.assertEqual(titles[:4], ['هیئت مؤسس', 'هیئت امنا',
                                      'شورای مؤسسه', 'رئیس مؤسسه'])

    def test_the_five_deputies_follow(self):
        titles = [row['title'] for row in org_chart.build()]
        for label in ('معاونت آموزشی', 'معاونت پژوهشی', 'معاونت اداری و مالی',
                      'معاونت دانشجویی', 'معاونت فنی و عمرانی'):
            self.assertIn(label, titles)

    def test_the_presidency_carries_its_offices(self):
        rows = {row['title']: row for row in org_chart.build()}
        kids = [kid['title'] for kid in rows['رئیس مؤسسه']['children']]
        self.assertIn('حراست', kids)
        self.assertIn('دفتر حقوقی', kids)
        self.assertIn('قائم مقام', kids)

    def test_the_deputies_come_from_the_menu_source(self):
        """یک منبع برای منو و چارت، وگرنه دو چیز متفاوت می‌گویند."""
        from core import vices

        menu = {row['label'] for row in vices.build()}
        listed = {row['title'] for row in org_chart.build()}
        self.assertTrue(menu.issubset(listed))

    def test_a_unit_without_a_page_has_no_link(self):
        rows = {row['title']: row for row in org_chart.build()}
        kids = {kid['title']: kid for kid in rows['رئیس مؤسسه']['children']}
        self.assertEqual(kids['دفتر حقوقی']['url'], '')
        self.assertTrue(kids['حراست']['url'])

    def test_every_link_actually_resolves(self):
        def walk(rows):
            for row in rows:
                if row['url']:
                    self.assertEqual(self.client.get(row['url']).status_code,
                                     200, row['title'])
                walk(row['children'])

        walk(org_chart.build())

    def test_the_count_includes_every_level(self):
        rows = org_chart.build()
        self.assertGreater(org_chart.count(rows), len(rows))
        self.assertEqual(org_chart.count([]), 0)


class ChartIndexPageTests(TestCase):

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')

    def _html(self):
        cache.clear()
        return self.client.get(reverse('core:about')).content.decode()

    def test_the_index_is_on_the_page(self):
        html = self._html()
        self.assertIn('chart-index', html)
        self.assertIn('راهنمای چارت', html)

    def test_it_is_collapsed_so_it_does_not_bury_the_chart(self):
        html = self._html()
        self.assertIn('<details class="chart-index', html)
        self.assertNotIn('<details class="chart-index mt-4" open', html)

    def test_the_deep_levels_are_rendered_too(self):
        """چارت سه سطح دارد؛ فهرست هم باید داشته باشد."""
        html = self._html()
        for label in ('ادارهٔ امتحانات', 'مرکز کامپیوتر',
                      'ادارهٔ تربیت بدنی'):
            self.assertIn(label, html)

    def test_a_unit_with_a_page_is_a_link(self):
        html = self._html()
        self.assertIn('<a class="chart-node', html)

    def test_a_unit_without_a_page_is_not_a_dead_link(self):
        html = self._html()
        self.assertIn('<span class="chart-node', html)

    def test_the_count_is_shown_in_persian_digits(self):
        html = self._html()
        head = html.split('chart-index-count')[1][:80]
        self.assertNotIn('0', head)
        self.assertIn('واحد', head)


class TheChartTreeIsGoneTests(TestCase):
    """موسسه خواست فقط تصویر چارت بماند."""

    def setUp(self):
        cache.clear()
        SiteSettings.objects.create(university_name_fa='موسسه')

    def test_the_page_no_longer_builds_a_node_tree(self):
        html = self.client.get(reverse('core:about')).content.decode()
        self.assertNotIn('org-chart-container', html)
        self.assertNotIn('org-node', html)

    def test_the_panel_no_longer_offers_the_second_form(self):
        from django.contrib import admin

        from core.models import OrganizationalChart

        self.assertNotIn(OrganizationalChart, admin.site._registry)

    def test_the_data_itself_is_untouched(self):
        """پنهان‌شدن از پنل نباید یعنی حذف داده."""
        from core.models import OrganizationalChart

        OrganizationalChart.objects.create(name='ریاست', node_type='president')
        self.assertEqual(OrganizationalChart.objects.count(), 1)
