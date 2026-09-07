"""واحدهای چارت باید بتوانند به صفحهٔ خودشان وصل شوند."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core import vices as structure
from core.models import VicePresidency, ViceUnit, ViceUnitLink


def _walk(rows):
    for row in rows:
        yield row
        yield from _walk(row['children'])


def _find(title):
    for vice in structure.build():
        for row in _walk(vice['children']):
            if row['title'] == title:
                return row
    return None


class AChartUnitCanBeGivenAnAddressTests(TestCase):
    """بیشترِ واحدهای چارت صفحهٔ اختصاصی ندارند و متن ساده بودند."""

    def setUp(self):
        cache.clear()
        ViceUnitLink.objects.all().delete()

    def test_without_a_link_it_stays_plain_text(self):
        self.assertEqual(_find('ادارهٔ امتحانات')['url'], '')

    def test_a_link_from_the_panel_is_used(self):
        ViceUnitLink.objects.create(
            title='ادارهٔ امتحانات', url='/امتحانات/', is_active=True)
        self.assertEqual(_find('ادارهٔ امتحانات')['url'], '/امتحانات/')

    def test_an_inactive_link_is_ignored(self):
        ViceUnitLink.objects.create(
            title='ادارهٔ امتحانات', url='/امتحانات/', is_active=False)
        self.assertEqual(_find('ادارهٔ امتحانات')['url'], '')

    def test_spelling_differences_do_not_break_the_match(self):
        """نیم‌فاصله و «ي» عربی نباید تطبیق را بشکنند."""
        ViceUnitLink.objects.create(
            title='اداره امتحانات', url='/امتحانات/', is_active=True)
        self.assertEqual(_find('ادارهٔ امتحانات')['url'], '/امتحانات/')

    def test_a_unit_that_already_has_a_page_is_untouched(self):
        """کتابخانه صفحهٔ واقعی دارد؛ جدول نباید جایش را بگیرد."""
        ViceUnitLink.objects.create(
            title='کتابخانه', url='/جای-اشتباه/', is_active=True)
        self.assertEqual(_find('کتابخانه')['url'], reverse('library:library'))

    def test_the_link_reaches_the_menu(self):
        ViceUnitLink.objects.create(
            title='ادارهٔ امتحانات', url='/امتحانات/', is_active=True)
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        menu = html.split('nav-dd-vices')[1]
        self.assertIn('href="/امتحانات/"', menu)

    def test_a_plain_unit_is_not_a_dead_link(self):
        cache.clear()
        html = self.client.get(reverse('core:home')).content.decode()
        menu = html.split('nav-dd-vices')[1]
        self.assertIn('nav-dd-sub is-plain', menu)


class APanelUnitCarriesItsOwnAddressTests(TestCase):
    """واحدهایی که خودِ موسسه در پنل ثبت می‌کند."""

    def setUp(self):
        cache.clear()
        ViceUnitLink.objects.all().delete()
        self.vice = VicePresidency.objects.create(
            vice_type='research', is_active=True)

    def test_a_unit_without_a_link_stays_plain(self):
        ViceUnit.objects.create(vice=self.vice, name='واحد بی‌صفحه',
                                is_active=True)
        self.assertEqual(_find('واحد بی‌صفحه')['url'], '')

    def test_its_own_link_is_used(self):
        ViceUnit.objects.create(vice=self.vice, name='واحد باصفحه',
                                link='/جایی/', is_active=True)
        self.assertEqual(_find('واحد باصفحه')['url'], '/جایی/')

    def test_the_shared_table_covers_it_too(self):
        ViceUnit.objects.create(vice=self.vice, name='واحد مشترک',
                                is_active=True)
        ViceUnitLink.objects.create(title='واحد مشترک', url='/مشترک/',
                                    is_active=True)
        self.assertEqual(_find('واحد مشترک')['url'], '/مشترک/')


class ThePanelHelpsFindWhatIsMissingTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(
            'modirlink', 'l@aab.ac.ir', 'Str0ng!Pass2026')
        self.client.force_login(self.staff)

    def test_the_form_lists_units_still_without_an_address(self):
        """وگرنه مدیر باید نام‌ها را از منو حدس بزند."""
        html = self.client.get(
            '/admin/core/viceunitlink/add/').content.decode()
        self.assertIn('بدون نشانی', html)
        self.assertIn('ادارهٔ امتحانات', html)

    def test_the_list_is_editable_in_place(self):
        from core.admin import ViceUnitLinkAdmin

        self.assertIn('url', ViceUnitLinkAdmin.list_editable)

    def test_a_unit_row_offers_a_link_box(self):
        from core.admin import ViceUnitAdmin

        self.assertIn('link', ViceUnitAdmin.list_editable)
