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
