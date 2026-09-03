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

    def test_each_body_lands_on_its_own_block(self):
        nav = self._nav()
        people = reverse('directory:people')
        for anchor in ('#founder', '#trustee', '#faculty', '#lecturer'):
            self.assertIn(people + anchor, nav)

    def test_the_page_has_those_anchors(self):
        from directory.models import DirectoryPerson

        DirectoryPerson.objects.create(
            category='founder', full_name='نمونهٔ مؤسس', is_active=True)
        html = self.client.get(
            reverse('directory:people')).content.decode()
        self.assertIn('id="founder"', html)


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
