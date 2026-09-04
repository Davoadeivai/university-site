"""باکس جستجو باید هر چیزی را که روی سایت هست پیدا کند."""
import json

from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicGroup, Department, Major
from core.models import Council, PresidencyOfficeUnit
from directory.models import DirectoryPerson


def _search(client, query):
    response = client.get('/api/live-search/', {'q': query})
    return json.loads(response.content.decode()).get('results', [])


def _urls(rows):
    return {row['url'] for row in rows}


class SearchFindsEveryPageTests(TestCase):
    """صفحه‌هایی که ماه‌های اخیر ساخته شدند، در جستجو نبودند."""

    def test_the_new_pages_are_reachable_from_the_box(self):
        pairs = [
            ('دانشکده', reverse('academics:departments')),
            ('رشته‌های تحصیلی', reverse('academics:majors')),
            ('گروه‌های آموزشی', reverse('academics:groups_list')),
            ('مدیران گروه', reverse('academics:group_heads')),
            ('شوراها', reverse('core:councils')),
            ('دفترچه تلفن', reverse('directory:staff')),
            ('سرفصل مصوب', reverse('directory:curricula')),
            ('مسیر پذیرش', reverse('core:student_path')),
        ]
        for query, url in pairs:
            self.assertIn(url, _urls(_search(self.client, query)), query)

    def test_each_deputy_has_its_own_hit(self):
        from core.vices import VICE_ORDER

        for vice_type, label, _icon in VICE_ORDER:
            url = reverse('core:vice_detail', args=[vice_type])
            self.assertIn(url, _urls(_search(self.client, label)), label)

    def test_each_body_of_the_institute_has_its_own_hit(self):
        from directory.views import PEOPLE_SECTIONS

        for slug, _key, label, _icon, _blurb in PEOPLE_SECTIONS:
            url = reverse('directory:people_section', args=[slug])
            self.assertIn(url, _urls(_search(self.client, label)), label)


class SearchFindsContentTests(TestCase):
    """ردیف‌های دیتابیس، نه فقط صفحه‌های ثابت."""

    def setUp(self):
        self.council = Council.objects.create(
            name='شورای آزمایشی', slug='azmayeshi-search', is_active=True,
            short_description='برای آزمون جستجو')
        self.unit = PresidencyOfficeUnit.objects.create(
            slug='dabirkhane-azmayeshi', title='دبیرخانه آزمایشی',
            content='متن نمونه')
        faculty = Department.objects.create(
            name='دانشکده آزمایشی', slug='azmayeshi-dep', is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه آزمایشی', slug='azmayeshi-grp',
            is_active=True)
        self.major = Major.objects.create(
            department=faculty, name='رشتهٔ آزمایشی', slug='azmayeshi-major',
            degree='master', is_active=True)
        self.person = DirectoryPerson.objects.create(
            category='trustee', full_name='امنای آزمایشی', is_active=True)

    def test_a_council_is_found_and_links_to_its_page(self):
        rows = _search(self.client, 'شورای آزمایشی')
        self.assertIn(self.council.get_absolute_url(), _urls(rows))

    def test_a_presidency_unit_is_found(self):
        rows = _search(self.client, 'دبیرخانه آزمایشی')
        self.assertIn(
            reverse('core:presidency_office_unit', args=[self.unit.slug]),
            _urls(rows))

    def test_a_group_and_a_major_are_found(self):
        self.assertIn(self.group.get_absolute_url(),
                      _urls(_search(self.client, 'گروه آزمایشی')))
        self.assertIn(self.major.get_absolute_url(),
                      _urls(_search(self.client, 'رشتهٔ آزمایشی')))

    def test_a_person_lands_on_the_page_of_their_own_body(self):
        """پیش از این همه به فهرست کلی می‌رفتند."""
        rows = _search(self.client, 'امنای آزمایشی')
        self.assertIn(
            reverse('directory:people_section', args=['هیات-امنا']),
            _urls(rows))

    def test_every_result_carries_a_link_that_opens(self):
        for query in ('شورای آزمایشی', 'گروه آزمایشی', 'رشتهٔ آزمایشی'):
            for row in _search(self.client, query):
                self.assertTrue(row['url'], row)
                self.assertEqual(
                    self.client.get(row['url']).status_code, 200, row['url'])

    def test_an_empty_query_returns_nothing(self):
        self.assertEqual(_search(self.client, ''), [])
