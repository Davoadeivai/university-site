"""ارکان موسسه در منو، و جابه‌جایی دبیرخانه‌ها."""
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import PresidencyOfficeUnit


class ArkanMenuTests(TestCase):
    """«هیئت علمی» یک آیتم بود و به صفحه‌ای با پنج بخش می‌رفت."""

    def setUp(self):
        cache.clear()

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def _about_menu(self):
        return self._nav().split('درباره موسسه')[1].split('</li>\n\n')[0]

    def test_the_branch_is_called_arkan(self):
        nav = self._nav()
        self.assertIn('ارکان موسسه', nav)

    def test_the_old_single_item_label_is_gone(self):
        """«هیئت علمی» تنها، جای «ارکان موسسه» را گرفته بود."""
        nav = self._nav()
        self.assertNotIn('>هیئت علمی<', nav)

    def test_the_two_founding_bodies_are_listed(self):
        nav = self._nav()
        self.assertIn('هیئت مؤسس', nav)
        self.assertIn('هیئت امنا', nav)

    def test_the_rest_of_the_people_page_keeps_a_home(self):
        """اعضای هیئت علمی، مدیران گروه و مدرسین گم نشدند."""
        nav = self._nav()
        self.assertIn('اعضای هیئت علمی', nav)
        self.assertIn('مدرسین', nav)
        self.assertIn(reverse('academics:group_heads'), nav)

    def test_each_body_has_a_page_of_its_own(self):
        """پیش از این همه به یک صفحه می‌رفتند و فقط لنگر فرق داشت."""
        nav = self._nav()
        for slug in ('هیات-موسس', 'هیات-امنا', 'هیات-علمی', 'مدرسین'):
            self.assertIn(
                reverse('directory:people_section', args=[slug]), nav)

    def test_those_pages_open_and_show_only_their_own_people(self):
        from directory.models import DirectoryPerson

        DirectoryPerson.objects.create(
            category='founder', full_name='نمونهٔ مؤسس', is_active=True)
        DirectoryPerson.objects.create(
            category='lecturer', full_name='نمونهٔ مدرس', is_active=True)

        founders = self.client.get(
            reverse('directory:people_section',
                    args=['هیات-موسس'])).content.decode()
        self.assertIn('نمونهٔ مؤسس', founders)
        self.assertNotIn('نمونهٔ مدرس', founders)

    def test_the_full_list_still_exists(self):
        self.assertIn(reverse('directory:people'), self._nav())


class SecretariatsMovedTests(TestCase):
    """دبیرخانه‌ها زیر رکنِ خودشان می‌نشینند، نه زیر ریاست."""

    def setUp(self):
        cache.clear()
        call_command('seed_presidency', stdout=StringIO())

    def _nav(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('id="mainNav"')[1].split('</nav>')[0]

    def _presidency_menu(self):
        """فهرست زیرِ «حوزه ریاست» — عنوان در یک عنصر جدا از فهرست است."""
        # نام دو بار در نوار هست: یک بار در کامنت قالب، یک بار روی
        # خودِ دکمه. آخری همان است که فهرست زیرش می‌آید.
        nav = self._nav()
        after = nav.rsplit('حوزه ریاست', 1)[1]
        return after.split('<ul')[1].split('</ul>')[0]

    def test_the_trustees_secretariat_left_the_presidency_menu(self):
        self.assertNotIn('dabirkhane-heyat-omana', self._presidency_menu())

    def test_it_sits_under_arkan_instead(self):
        nav = self._nav()
        self.assertIn(
            reverse('core:presidency_office_unit',
                    args=['dabirkhane-heyat-omana']), nav)

    def test_the_founders_secretariat_exists_now(self):
        unit = PresidencyOfficeUnit.objects.get(slug='dabirkhane-heyat-moases')
        self.assertEqual(unit.title, 'دبیرخانه هیأت مؤسس')
        self.assertTrue(unit.duty_list if hasattr(unit, 'duty_list')
                        else unit.duties)

    def test_its_page_opens(self):
        url = reverse('core:presidency_office_unit',
                      args=['dabirkhane-heyat-moases'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('هیأت مؤسس', response.content.decode())

    def test_the_menu_points_at_it(self):
        self.assertIn(
            reverse('core:presidency_office_unit',
                    args=['dabirkhane-heyat-moases']), self._nav())

    def test_the_presidency_keeps_its_own_secretariats(self):
        menu = self._presidency_menu()
        self.assertIn('dabirkhane-heyat-raise', menu)
        self.assertIn('dabirkhane-jazb', menu)


class PeopleSectionPagesTests(TestCase):
    """هر رکن، صفحهٔ خودش — نه پنج بخش زیر یک عنوان."""

    def setUp(self):
        cache.clear()
        from directory.models import DirectoryPerson

        for category, name in (
            ('founder', 'مؤسس نمونه'),
            ('trustee', 'امنای نمونه'),
            ('faculty', 'استاد نمونه'),
            ('group_head', 'مدیر گروه نمونه'),
            ('lecturer', 'مدرس نمونه'),
        ):
            DirectoryPerson.objects.create(
                category=category, full_name=name, is_active=True)

    def _page(self, slug):
        return self.client.get(
            reverse('directory:people_section', args=[slug]))

    def test_every_section_has_its_own_address(self):
        for slug in ('هیات-موسس', 'هیات-امنا', 'هیات-علمی',
                     'مدیران-گروه', 'مدرسین'):
            self.assertEqual(self._page(slug).status_code, 200, slug)

    def test_a_section_shows_only_its_own_people(self):
        html = self._page('هیات-امنا').content.decode()
        self.assertIn('امنای نمونه', html)
        for other in ('مؤسس نمونه', 'استاد نمونه', 'مدرس نمونه'):
            self.assertNotIn(other, html)

    def test_an_unknown_section_is_a_404(self):
        self.assertEqual(self._page('چیزی-نیست').status_code, 404)

    def test_each_page_offers_the_way_to_the_others(self):
        html = self._page('هیات-موسس').content.decode()
        self.assertIn('people-others', html)
        self.assertIn(
            reverse('directory:people_section', args=['هیات-امنا']), html)

    def test_the_full_list_links_into_each_page(self):
        html = self.client.get(reverse('directory:people')).content.decode()
        for slug in ('هیات-موسس', 'مدرسین'):
            self.assertIn(
                reverse('directory:people_section', args=[slug]), html)

    def test_an_empty_section_does_not_break(self):
        from directory.models import DirectoryPerson

        DirectoryPerson.objects.filter(category='lecturer').delete()
        response = self._page('مدرسین')
        self.assertEqual(response.status_code, 200)
        self.assertIn('مدرسین', response.content.decode())
