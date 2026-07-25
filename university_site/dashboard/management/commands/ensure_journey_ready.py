"""آماده‌سازی ترم، شهریه، دروس و تخصیص تدریس برای مسیر پس از پذیرش."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from academics.models import Course, Major
from admissions.models import Application, TuitionStructure
from accounts.models import UserProfile
from dashboard.models import Semester, TeachingAssignment, TuitionInstallmentPlan
from dashboard.onboarding import ensure_tuition_invoice


class Command(BaseCommand):
    help = 'فعال‌سازی ترم/شهریه/دروس برای مسیر پذیرش → انتخاب واحد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--national-id',
            default='',
            help='کد ملی متقاضی پذیرفته‌شده برای همگام‌سازی هدفمند',
        )

    def handle(self, *args, **options):
        today = date.today()
        year = today.year
        semester, created = Semester.objects.get_or_create(
            name=f'ترم جاری {year}',
            academic_year=f'{year}-{year + 1}',
            defaults={
                'semester_type': 'fall' if today.month >= 9 or today.month <= 1 else 'spring',
                'start_date': today - timedelta(days=14),
                'end_date': today + timedelta(days=120),
                'is_active': True,
                'registration_open': True,
            },
        )
        Semester.objects.exclude(pk=semester.pk).update(is_active=False)
        semester.is_active = True
        semester.registration_open = True
        semester.save(update_fields=['is_active', 'registration_open'])
        self.stdout.write(self.style.SUCCESS(
            f'Semester ready: {semester} (created={created}, registration_open=True)'
        ))

        plan, plan_created = TuitionInstallmentPlan.objects.get_or_create(
            academic_year=semester.academic_year,
            defaults={
                'ratio_initial': 40,
                'ratio_mid': 30,
                'ratio_exam': 30,
                'due_days_initial': 7,
                'due_days_mid': 60,
                'due_days_exam': 100,
                'reminder_days_before': 3,
                'is_active': True,
            },
        )
        self.stdout.write(
            f'Installment plan {plan.academic_year}: '
            f'{plan.ratio_initial}/{plan.ratio_mid}/{plan.ratio_exam} (new={plan_created})'
        )

        nid = (options.get('national_id') or '').strip()
        apps = Application.objects.filter(status='accepted').select_related('desired_major')
        if nid:
            apps = apps.filter(national_id=nid)
        majors = []
        for app in apps:
            if app.desired_major_id and app.desired_major not in majors:
                majors.append(app.desired_major)
        if not majors:
            m = Major.objects.filter(is_active=True).first()
            if m:
                majors = [m]

        professor = (
            User.objects.filter(profile__role='professor').order_by('id').first()
            or User.objects.filter(is_staff=True).order_by('id').first()
        )
        if professor is None:
            professor, _ = User.objects.get_or_create(
                username='professor_journey',
                defaults={'first_name': 'استاد', 'last_name': 'نمونه'},
            )
            UserProfile.objects.update_or_create(
                user=professor,
                defaults={'role': 'professor'},
            )

        for major in majors:
            ts, ts_created = TuitionStructure.objects.get_or_create(
                major=major,
                academic_year=semester.academic_year,
                defaults={
                    'fixed_fee': 5_000_000,
                    'theory_fee': 350_000,
                    'practical_fee': 400_000,
                    'lab_fee': 450_000,
                    'is_active': True,
                },
            )
            if not ts.is_active:
                ts.is_active = True
                ts.save(update_fields=['is_active'])
            self.stdout.write(f'Tuition {major.name}: ok (new={ts_created}) amount_base={ts.fixed_fee}')

            course_specs = [
                (f'{major.name[:20]} — درس تخصصی ۱', 'JRN101', 3, 'شنبه ۱۰-۱۲', 'کلاس ۱۰۱'),
                (f'{major.name[:20]} — درس تخصصی ۲', 'JRN102', 3, 'یکشنبه ۱۴-۱۶', 'کلاس ۱۰۲'),
                (f'{major.name[:20]} — درس تخصصی ۳', 'JRN103', 2, 'دوشنبه ۸-۱۰', 'کلاس ۱۰۳'),
            ]
            for name, code, credits, schedule, classroom in course_specs:
                course, _ = Course.objects.get_or_create(
                    major=major,
                    code=code,
                    defaults={
                        'name': name,
                        'credits': credits,
                        'course_type': 'specialized',
                        'semester': 1,
                    },
                )
                TeachingAssignment.objects.update_or_create(
                    professor=professor,
                    course=course,
                    semester=semester,
                    defaults={
                        'class_schedule': schedule,
                        'classroom': classroom,
                        'is_active': True,
                        'department': major.department,
                    },
                )
            self.stdout.write(self.style.SUCCESS(f'Courses/TA ready for {major.name}'))

        # فاکتور شهریه برای کاربران با کد ملی پذیرش‌شده
        for app in apps:
            user = User.objects.filter(username=app.national_id).first()
            if not user:
                profile = UserProfile.objects.filter(national_id=app.national_id).select_related('user').first()
                user = profile.user if profile else None
            if user:
                if app.desired_major_id:
                    UserProfile.objects.filter(user=user).update(major=app.desired_major)
                inv = ensure_tuition_invoice(user, semester)
                self.stdout.write(f'Invoice for {app.national_id}: {inv.amount if inv else "skipped"}')

        self.stdout.write(self.style.SUCCESS('Journey readiness complete.'))
