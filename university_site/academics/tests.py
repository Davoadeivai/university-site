from django.test import TestCase

# Create your tests here.
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from academics.management.commands.import_major_codes import best_match, tokens
from academics.models import Department, Major


def _department():
    """Major.department در دیتابیس NOT NULL است."""
    dept, _ = Department.objects.get_or_create(
        slug='test-dept', defaults={'name': 'دانشکده آزمون'})
    return dept


class MajorCodeMatchingTests(TestCase):
    """سند و دیتابیس یک رشته را جور دیگری می‌نویسند."""

    def test_parenthesised_and_dashed_forms_are_the_same_major(self):
        self.assertEqual(
            tokens('مدیریت بازرگانی (گرایش بازاریابی)'),
            tokens('مدیریت بازرگانی - گرایش بازاریابی'))

    def test_arabic_letters_normalise(self):
        self.assertEqual(tokens('مديريت صنعتي'), tokens('مدیریت صنعتی'))

    def test_a_close_name_matches(self):
        major = Major.objects.create(
            name='الکتروتکنیک برق صنعتی', slug='e1', degree='associate_cont',
            department=_department())
        found, score = best_match(
            {'name': 'الکتروتکنیک (برق صنعتی)'}, [major])
        self.assertEqual(found, major)
        self.assertGreaterEqual(score, 0.7)

    def test_a_narrower_major_is_not_matched_to_a_broader_one(self):
        """«مهندسی برق» و «مهندسی برق قدرت» دو رشتهٔ متفاوت‌اند."""
        broad = Major.objects.create(
            name='تکنولوژی مهندسی برق', slug='e2', degree='bachelor_disc',
            department=_department())
        found, _score = best_match({'name': 'مهندسی برق – قدرت'}, [broad])
        self.assertIsNone(found)

    def test_an_empty_candidate_pool_returns_nothing(self):
        self.assertEqual(best_match({'name': 'حسابداری'}, [])[0], None)


class ImportMajorCodesTests(TestCase):

    def setUp(self):
        self.major = Major.objects.create(
            name='حسابداری و بازرگانی', slug='hb', degree='associate_cont',
            department=_department())

    def test_credits_and_code_are_filled(self):
        call_command('import_major_codes', stdout=StringIO())
        self.major.refresh_from_db()
        self.assertEqual(self.major.code, '9144')
        self.assertEqual(self.major.total_credits, 73)
        self.assertEqual(self.major.internship_hours, 240)

    def test_a_value_set_in_the_admin_is_kept(self):
        self.major.total_credits = 99
        self.major.save()
        call_command('import_major_codes', stdout=StringIO())
        self.major.refresh_from_db()
        self.assertEqual(self.major.total_credits, 99)

    def test_overwrite_replaces_it(self):
        self.major.total_credits = 99
        self.major.save()
        call_command('import_major_codes', '--overwrite', stdout=StringIO())
        self.major.refresh_from_db()
        self.assertEqual(self.major.total_credits, 73)

    def test_dry_run_writes_nothing(self):
        call_command('import_major_codes', '--dry-run', stdout=StringIO())
        self.major.refresh_from_db()
        self.assertEqual(self.major.total_credits, 0)

    def test_rows_that_match_nothing_are_reported(self):
        out = StringIO()
        call_command('import_major_codes', stdout=out)
        self.assertIn('نخورد', out.getvalue())

    def test_running_twice_changes_nothing_the_second_time(self):
        call_command('import_major_codes', stdout=StringIO())
        second = StringIO()
        call_command('import_major_codes', stdout=second)
        self.assertIn('0 رشته پر شد', second.getvalue())


class CreateMissingMajorTests(TestCase):
    """ساخت رشته فقط با کد صریح، نه با «هرچه تطبیق نخورد».

    نسخهٔ اول هر ردیف بی‌تطبیق را می‌ساخت و ۹ رشته درست کرد که ۶ تای
    آن‌ها صرفاً نوشتار دیگری از رشته‌های موجود بودند — یعنی ۶ رکورد
    تکراری. کد وزارت کلید بدون ابهامی است و تصمیم را دست آدم می‌گذارد.
    """

    def setUp(self):
        _department()

    def test_nothing_is_created_without_the_flag(self):
        before = Major.objects.count()
        call_command('import_major_codes', stdout=StringIO())
        self.assertEqual(Major.objects.count(), before)

    def test_only_the_named_code_is_created(self):
        call_command('import_major_codes', '--create', '8381',
                     stdout=StringIO())
        self.assertTrue(Major.objects.filter(code='8381').exists())
        self.assertFalse(Major.objects.filter(code='9353').exists())

    def test_a_created_major_is_inactive(self):
        call_command('import_major_codes', '--create', '8381',
                     stdout=StringIO())
        self.assertFalse(Major.objects.get(code='8381').is_active)

    def test_a_created_major_carries_its_credits(self):
        call_command('import_major_codes', '--create', '8381',
                     stdout=StringIO())
        self.assertEqual(Major.objects.get(code='8381').total_credits, 147)

    def test_running_twice_creates_one_record(self):
        for _ in range(2):
            call_command('import_major_codes', '--create', '8381',
                         stdout=StringIO())
        self.assertEqual(Major.objects.filter(code='8381').count(), 1)

    def test_the_group_is_inferred_from_the_name(self):
        from academics.models import AcademicGroup
        group = AcademicGroup.objects.create(
            name='گروه علوم اجتماعی', slug='social', department=_department())
        call_command('import_major_codes', '--create', '8381',
                     stdout=StringIO())
        self.assertEqual(Major.objects.get(code='8381').group, group)


class AcademicStructureTests(TestCase):
    """گروه آموزشی واحد واقعی این موسسه است، نه دانشکده.

    هر ۵۸ رشته زیر یک دانشکده («تحصیلات تکمیلی») ثبت شده بودند، پس
    صفحهٔ یک رشتهٔ کاردانی هم همان را نشان می‌داد.
    """

    def setUp(self):
        self.dept = _department()

    def _group(self, name):
        from academics.models import AcademicGroup
        return AcademicGroup.objects.create(
            name=name, slug=name.replace(' ', '-'), department=self.dept)

    def test_an_orphan_major_is_linked_to_its_group(self):
        group = self._group('گروه حسابداری')
        major = Major.objects.create(
            name='حسابداری - گرایش حسابرسی', slug='hb-1', degree='master',
            department=self.dept)
        call_command('tidy_academic_structure', stdout=StringIO())
        major.refresh_from_db()
        self.assertEqual(major.group, group)

    def test_a_specific_keyword_wins_over_a_general_one(self):
        """«مدیریت بازرگانی» نباید با قاعدهٔ «مدیریت» به گروه دیگری برود."""
        self._group('گروه مدیریت صنعتی و مالی')
        bazargani = self._group('گروه مدیریت بازرگانی')
        major = Major.objects.create(
            name='مدیریت بازرگانی - گرایش بازاریابی', slug='mb-1',
            degree='master', department=self.dept)
        call_command('tidy_academic_structure', stdout=StringIO())
        major.refresh_from_db()
        self.assertEqual(major.group, bazargani)

    def test_a_major_with_a_group_is_left_alone(self):
        keep = self._group('گروه کامپیوتر')
        other = self._group('گروه برق')
        major = Major.objects.create(
            name='مهندسی برق', slug='b-1', degree='bachelor_cont',
            department=self.dept, group=keep)
        call_command('tidy_academic_structure', stdout=StringIO())
        major.refresh_from_db()
        self.assertEqual(major.group, keep, 'گروه دستی بازنویسی شد')

    def test_an_unrecognised_name_is_reported_not_guessed(self):
        Major.objects.create(
            name='رشتهٔ ناشناخته', slug='x-1', degree='master',
            department=self.dept)
        out = StringIO()
        call_command('tidy_academic_structure', stdout=out)
        self.assertIn('معلوم نشد', out.getvalue())

    def test_purge_removes_a_latin_named_empty_group(self):
        self._group('bargh')
        call_command('tidy_academic_structure', '--purge-empty',
                     stdout=StringIO())
        from academics.models import AcademicGroup
        self.assertFalse(AcademicGroup.objects.filter(name='bargh').exists())

    def test_purge_keeps_a_persian_named_empty_group(self):
        """گروه واقعیِ خالی شاید رشته‌اش هنوز ثبت نشده باشد."""
        self._group('گروه علوم پایه و معارف')
        call_command('tidy_academic_structure', '--purge-empty',
                     stdout=StringIO())
        from academics.models import AcademicGroup
        self.assertTrue(
            AcademicGroup.objects.filter(name='گروه علوم پایه و معارف').exists())

    def test_dry_run_writes_nothing(self):
        self._group('گروه حسابداری')
        major = Major.objects.create(
            name='حسابداری', slug='h-1', degree='master', department=self.dept)
        call_command('tidy_academic_structure', '--dry-run', stdout=StringIO())
        major.refresh_from_db()
        self.assertIsNone(major.group)

    def test_the_major_page_shows_the_group_not_the_department(self):
        """نشان کنار نام رشته باید گروه باشد، نه دانشکده.

        مسیر بالای صفحه دانشکده را می‌آورد — آنجا جای درستش است و
        راهی به بالا می‌دهد؛ چیزی که اینجا سنجیده می‌شود خودِ کارت
        رشته است.
        """
        group = self._group('گروه کامپیوتر')
        major = Major.objects.create(
            name='مهندسی کامپیوتر', slug='mk-1', degree='bachelor_cont',
            department=self.dept, group=group, is_active=True)
        body = self.client.get(major.get_absolute_url()).content.decode()
        card = body.split('<span class="uni-card-badge">')[1].split(
            '<div class="row')[0]
        self.assertIn('گروه کامپیوتر', card)
        self.assertNotIn('دانشکده آزمون', card)
