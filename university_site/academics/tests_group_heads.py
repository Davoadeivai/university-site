"""ثبت مدیر گروه‌ها از فهرست افراد موسسه."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from academics.models import AcademicGroup, Department
from directory.models import DirectoryPerson
from faculty.models import Professor


GROUPS = [
    'گروه برق، الکترونیک و مخابرات',
    'گروه کامپیوتر',
    'گروه مکانیک',
    'گروه معماری و نقشه‌کشی',
    'گروه حسابداری',
    'گروه مدیریت بازرگانی',
    'گروه مدیریت صنعتی و مالی',
    'گروه روان‌شناسی',
    'گروه علوم تربیتی - مدیریت آموزشی',
    'گروه علوم اجتماعی',
]

HEADS = [
    ('جلال قنبری جلودار', 'مدیر گروه مدیریت آموزشی'),
    ('سجاد سالاری', 'مدیر گروه حسابداری'),
    ('فاطمه نمازی', 'مدیر گروه برق و کامپیوتر'),
    ('حسن عمرانی', 'مدیر گروه مکانیک و معماری'),
    ('علی فرنگی', 'مدیر گروه مدیریت'),
    ('مسعود باباخانی', 'مدیر گروه حسابداری'),
    ('هانیه دلیران چمن‌زمین', 'مدیر گروه مدیریت بازرگانی'),
    ('حسینعلی قربانی', 'مدیر گروه روان‌شناسی'),
    ('حسن فارسیجانی', 'مدیر گروه مدیریت صنعتی (ارشد)'),
    ('محمدرضا خسروی مقدم', 'مدیر گروه مدیریت صنعتی'),
]


def _run(*args):
    call_command('set_group_heads', *args, stdout=StringIO())


def _head(name):
    return AcademicGroup.objects.get(name=name)


class GroupHeadsFromDirectoryTests(TestCase):
    """یازده گروه داشتیم و هیچ‌کدام مدیرش ثبت نشده بود."""

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone', order=1, is_active=True)
        for index, name in enumerate(GROUPS, start=1):
            AcademicGroup.objects.create(
                department=faculty, name=name, slug='g%d' % index,
                order=index, is_active=True)
        for index, (name, position) in enumerate(HEADS, start=1):
            DirectoryPerson.objects.create(
                category='group_head', full_name=name, position=position,
                order=index, is_active=True)

    def test_each_head_lands_on_the_group_of_their_title(self):
        _run()
        self.assertEqual(_head('گروه روان‌شناسی').head_name, 'حسینعلی قربانی')
        self.assertEqual(
            _head('گروه مدیریت بازرگانی').head_name, 'هانیه دلیران چمن‌زمین')
        self.assertEqual(
            _head('گروه علوم تربیتی - مدیریت آموزشی').head_name,
            'جلال قنبری جلودار')

    def test_a_head_of_two_subjects_reaches_both_groups(self):
        """«مدیر گروه برق و کامپیوتر» یعنی دو گروه، نه یکی."""
        _run()
        self.assertEqual(
            _head('گروه برق، الکترونیک و مخابرات').head_name, 'فاطمه نمازی')
        self.assertEqual(_head('گروه کامپیوتر').head_name, 'فاطمه نمازی')
        self.assertEqual(_head('گروه مکانیک').head_name, 'حسن عمرانی')
        self.assertEqual(
            _head('گروه معماری و نقشه‌کشی').head_name, 'حسن عمرانی')

    def test_a_group_gets_one_name_not_two(self):
        """موسسه برای حسابداری دو نفر نوشته؛ کارت باید یک نام نشان دهد."""
        _run()
        self.assertEqual(_head('گروه حسابداری').head_name, 'سجاد سالاری')

    def test_the_second_name_is_reported_not_dropped_silently(self):
        out = StringIO()
        call_command('set_group_heads', stdout=out)
        report = out.getvalue()
        self.assertIn('مسعود باباخانی', report)
        self.assertIn('گروه حسابداری', report)

    def test_the_note_in_the_title_is_kept(self):
        _run()
        self.assertEqual(_head('گروه مدیریت صنعتی و مالی').head_name,
                         'حسن فارسیجانی (ارشد)')

    def test_a_general_title_does_not_squat_on_a_specific_group(self):
        """«مدیر گروه مدیریت» نباید کنار «مدیر گروه مدیریت بازرگانی» بنشیند."""
        _run()
        for name in ('گروه مدیریت بازرگانی', 'گروه مدیریت صنعتی و مالی',
                     'گروه علوم تربیتی - مدیریت آموزشی'):
            self.assertNotIn('علی فرنگی', _head(name).head_name, name)

    def test_a_head_without_a_group_is_reported_not_forced(self):
        out = StringIO()
        call_command('set_group_heads', stdout=out)
        self.assertIn('علی فرنگی', out.getvalue())

    def test_a_group_nobody_manages_stays_empty(self):
        _run()
        self.assertEqual(_head('گروه علوم اجتماعی').head_name, '')

    def test_a_faculty_record_is_linked_instead_of_typed(self):
        """اگر مدیر در هیئت علمی پرونده دارد، عکس و مرتبه‌اش هم بیاید."""
        professor = Professor.objects.create(
            first_name='حسینعلی', last_name='قربانی', rank='assistant',
            is_active=True)
        _run()
        group = _head('گروه روان‌شناسی')
        self.assertEqual(group.head_professor_id, professor.pk)
        self.assertEqual(group.head, '')
        self.assertEqual(group.head_name, 'حسینعلی قربانی')

    def test_a_name_written_by_hand_survives(self):
        group = _head('گروه کامپیوتر')
        group.head = 'دکتر دست‌نویس'
        group.save(update_fields=['head'])
        _run()
        self.assertEqual(_head('گروه کامپیوتر').head_name, 'دکتر دست‌نویس')

    def test_replace_overwrites_it(self):
        group = _head('گروه کامپیوتر')
        group.head = 'دکتر دست‌نویس'
        group.save(update_fields=['head'])
        _run('--replace')
        self.assertEqual(_head('گروه کامپیوتر').head_name, 'فاطمه نمازی')

    def test_dry_run_writes_nothing(self):
        _run('--dry-run')
        self.assertEqual(_head('گروه روان‌شناسی').head_name, '')

    def test_running_twice_changes_nothing(self):
        _run()
        first = {g.name: g.head_name for g in AcademicGroup.objects.all()}
        _run()
        second = {g.name: g.head_name for g in AcademicGroup.objects.all()}
        self.assertEqual(first, second)

    def test_an_empty_directory_falls_back_to_the_document(self):
        """اگر فهرست افراد پر نشده باشد، همان ده نام سند به کار می‌رود."""
        DirectoryPerson.objects.all().delete()
        _run()
        self.assertEqual(_head('گروه روان‌شناسی').head_name, 'حسینعلی قربانی')


class GroupHeadsOnThePageTests(TestCase):
    """نامی که ثبت شد باید روی صفحهٔ مدیران دیده شود."""

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone', order=1, is_active=True)
        AcademicGroup.objects.create(
            department=faculty, name='گروه روان‌شناسی', slug='ravan',
            order=1, is_active=True)
        DirectoryPerson.objects.create(
            category='group_head', full_name='حسینعلی قربانی',
            position='مدیر گروه روان‌شناسی', is_active=True)

    def test_the_name_reaches_the_page(self):
        from django.urls import reverse

        _run()
        html = self.client.get(
            reverse('academics:group_heads')).content.decode()
        self.assertIn('حسینعلی قربانی', html)
        self.assertNotIn('هنوز ثبت نشده', html)


class GroupBlurbTests(TestCase):
    """معرفی گروه، بدون تکرار نامش در آغاز.

    روی کارت، نام گروه یک خط بالای معرفی است و تقریباً همهٔ معرفی‌ها
    با «گروه آموزشی فلان …» شروع می‌شدند — همان چند کلمه، دو بار.
    """

    def setUp(self):
        self.faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-blurb', order=1,
            is_active=True)

    def _group(self, name, description):
        return AcademicGroup.objects.create(
            department=self.faculty, name=name,
            slug='b-%d' % AcademicGroup.objects.count(),
            description=description, is_active=True)

    def test_the_name_is_trimmed_from_the_front(self):
        group = self._group(
            'گروه کامپیوتر',
            'گروه کامپیوتر با تمرکز بر مهندسی نرم‌افزار فعالیت می‌کند.')
        self.assertEqual(
            group.blurb, 'با تمرکز بر مهندسی نرم‌افزار فعالیت می‌کند.')

    def test_the_word_amoozeshi_goes_too(self):
        group = self._group(
            'گروه برق، الکترونیک و مخابرات',
            'گروه آموزشی برق، الکترونیک و مخابرات با هدف تربیت مهندسان.')
        self.assertEqual(group.blurb, 'با هدف تربیت مهندسان.')

    def test_a_half_space_does_not_fool_it(self):
        """نام «نقشه کشی» است و متن «نقشه‌کشی» می‌نویسد."""
        group = self._group(
            'گروه معماری و نقشه‌کشی',
            'گروه معماری و نقشه‌کشی با ارائه آموزش‌های تخصصی.')
        self.assertEqual(group.blurb, 'با ارائه آموزش‌های تخصصی.')

    def test_a_description_that_does_not_repeat_is_untouched(self):
        group = self._group('گروه مکانیک', 'مبانی طراحی و ساخت و تولید.')
        self.assertEqual(group.blurb, 'مبانی طراحی و ساخت و تولید.')

    def test_an_empty_description_stays_empty(self):
        self.assertEqual(self._group('گروه خالی', '').blurb, '')

    def test_the_stored_text_is_not_changed(self):
        """متن پنل دست‌نخورده می‌ماند؛ بریدن فقط روی صفحه است."""
        group = self._group('گروه کامپیوتر', 'گروه کامپیوتر با تمرکز بر …')
        group.refresh_from_db()
        self.assertTrue(group.description.startswith('گروه کامپیوتر'))

    def test_the_card_uses_it(self):
        from django.urls import reverse

        self._group('گروه کامپیوتر',
                    'گروه کامپیوتر با تمرکز بر مهندسی نرم‌افزار.')
        html = self.client.get(
            reverse('academics:groups_list')).content.decode()
        card = html.split('dept-card')[1]
        self.assertIn('با تمرکز بر مهندسی نرم‌افزار.', card)
        self.assertEqual(card.count('گروه کامپیوتر'), 1)


class SelfCorrectionTests(TestCase):
    """آنچه خودِ دستور قبلاً نوشته، باید بتواند اصلاحش کند.

    روی سرور، اجرای پیشین دو نام را کنار هم نوشته بود؛ اجرای بعدی
    بدون ‎--replace‎ آن را «دست‌نویس مدیر» می‌دید و برای همیشه رد
    می‌کرد.
    """

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-fix', order=1, is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه حسابداری', slug='hesab-fix',
            order=1, is_active=True)
        for index, (name, position) in enumerate(
                [('سجاد سالاری', 'مدیر گروه حسابداری'),
                 ('مسعود باباخانی', 'مدیر گروه حسابداری')], start=1):
            DirectoryPerson.objects.create(
                category='group_head', full_name=name, position=position,
                order=index, is_active=True)

    def test_the_old_two_name_text_is_replaced(self):
        self.group.head = 'سجاد سالاری و مسعود باباخانی'
        self.group.save(update_fields=['head'])
        _run()
        self.group.refresh_from_db()
        self.assertEqual(self.group.head, 'سجاد سالاری')

    def test_a_hand_written_name_is_still_safe(self):
        self.group.head = 'دکتر کسی که مدیر نوشته'
        self.group.save(update_fields=['head'])
        _run()
        self.group.refresh_from_db()
        self.assertEqual(self.group.head, 'دکتر کسی که مدیر نوشته')

    def test_a_photo_of_the_previous_head_does_not_stay(self):
        """عکس مدیر قبلی، عکس این یکی نیست."""
        self.group.head = 'مدیر پیشین'
        self.group.head_photo = 'groups/old-head.jpg'
        self.group.save(update_fields=['head', 'head_photo'])
        _run('--replace')
        self.group.refresh_from_db()
        self.assertEqual(self.group.head, 'سجاد سالاری')
        self.assertFalse(self.group.head_photo)


class GroupNameWithoutTheWordGroupTests(TestCase):
    """«مدیر گروه گروه حسابداری» روی صفحه نوشته می‌شد."""

    def setUp(self):
        faculty = Department.objects.create(
            name='دانشکده نمونه', slug='nemoone-bare', order=1, is_active=True)
        self.group = AcademicGroup.objects.create(
            department=faculty, name='گروه مدیریت صنعتی و مالی',
            slug='sanati-bare', order=1, is_active=True,
            head='حسن فارسیجانی')

    def test_the_property_drops_the_prefix(self):
        self.assertEqual(self.group.bare_name, 'مدیریت صنعتی و مالی')

    def test_a_name_without_the_prefix_is_untouched(self):
        self.group.name = 'مدیریت بازرگانی'
        self.assertEqual(self.group.bare_name, 'مدیریت بازرگانی')

    def test_the_page_says_it_once(self):
        from django.urls import reverse

        html = self.client.get(
            self.group.get_absolute_url()).content.decode()
        self.assertIn('مدیر گروه مدیریت صنعتی و مالی', html)
        self.assertNotIn('مدیر گروه گروه', html)
        self.assertEqual(reverse('academics:group_detail',
                                 args=[self.group.slug]),
                         self.group.get_absolute_url())

    def _body(self):
        """متنِ خودِ صفحه — فوتر هم «اطلاعات تماس» دارد."""
        html = self.client.get(
            self.group.get_absolute_url()).content.decode()
        return html.split('<footer')[0]

    def test_an_empty_contact_card_is_not_drawn(self):
        self.assertNotIn('اطلاعات تماس', self._body())

    def test_the_contact_card_appears_when_there_is_something_to_say(self):
        self.group.phone = '۰۱۱-۳۵۷۵۰۸۱۰'
        self.group.save(update_fields=['phone'])
        self.assertIn('اطلاعات تماس', self._body())

    def test_the_majors_box_uses_the_site_palette(self):
        html = self.client.get(
            self.group.get_absolute_url()).content.decode()
        self.assertNotIn('#1a2e1a', html)
        self.assertNotIn('#f97316', html)
