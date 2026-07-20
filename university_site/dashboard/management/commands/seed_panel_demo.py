from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import Course, Major
from accounts.models import UserProfile
from dashboard.models import (
    Assignment,
    Enrollment,
    ExamSchedule,
    Payment,
    Semester,
    StudentRequest,
    TeachingAssignment,
)


class Command(BaseCommand):
    help = 'ایجاد داده نمونه پنل دانشجو/استاد (ترم، ثبت‌نام، نمره، درخواست، تکلیف)'

    def handle(self, *args, **options):
        major = Major.objects.filter(is_active=True).first()
        if not major:
            self.stderr.write('هیچ رشته‌ای یافت نشد. ابتدا seed_group_majors را اجرا کنید.')
            return

        # درس‌ها
        courses = []
        for name, code, credits in [
            ('برنامه‌نویسی پیشرفته', 'CS201', 3),
            ('پایگاه داده', 'CS301', 3),
            ('ریاضی مهندسی', 'MA201', 3),
        ]:
            course, _ = Course.objects.get_or_create(
                major=major,
                code=code,
                defaults={'name': name, 'credits': credits, 'course_type': 'specialized', 'semester': 3},
            )
            if course.name != name:
                course.name = name
                course.credits = credits
                course.save(update_fields=['name', 'credits'])
            courses.append(course)

        today = date.today()
        year = today.year
        semester, _ = Semester.objects.get_or_create(
            name=f'ترم فعال {year}',
            academic_year=f'{year}-{year + 1}',
            defaults={
                'semester_type': 'fall' if today.month >= 9 or today.month <= 1 else 'spring',
                'start_date': today - timedelta(days=30),
                'end_date': today + timedelta(days=120),
                'is_active': True,
                'registration_open': True,
            },
        )
        Semester.objects.exclude(pk=semester.pk).update(is_active=False)
        semester.is_active = True
        semester.save(update_fields=['is_active'])

        # کاربران نمونه
        student, created = User.objects.get_or_create(
            username='student1',
            defaults={'first_name': 'علی', 'last_name': 'محمدی', 'email': 'student1@uni.local'},
        )
        if created:
            student.set_password('student123')
            student.save()
        UserProfile.objects.update_or_create(
            user=student,
            defaults={'role': 'student', 'student_id': '1400123456'},
        )

        professor, created = User.objects.get_or_create(
            username='professor1',
            defaults={'first_name': 'سارا', 'last_name': 'احمدی', 'email': 'professor1@uni.local'},
        )
        if created:
            professor.set_password('professor123')
            professor.save()
        UserProfile.objects.update_or_create(
            user=professor,
            defaults={'role': 'professor', 'student_id': 'P-1001', 'department': 'فنی مهندسی'},
        )

        staff, created = User.objects.get_or_create(
            username='staff1',
            defaults={'first_name': 'رضا', 'last_name': 'کریمی', 'email': 'staff1@uni.local'},
        )
        if created:
            staff.set_password('staff123')
            staff.save()
        UserProfile.objects.update_or_create(
            user=staff,
            defaults={'role': 'staff', 'student_id': 'S-2001'},
        )

        for course in courses:
            TeachingAssignment.objects.get_or_create(
                professor=professor,
                course=course,
                semester=semester,
                defaults={
                    'classroom': f'A-{course.code[-3:]}',
                    'class_schedule': 'شنبه و دوشنبه ۱۰–۱۲',
                    'is_active': True,
                },
            )
            en, _ = Enrollment.objects.get_or_create(
                student=student,
                course=course,
                semester=semester,
                defaults={'status': 'in_progress'},
            )
            if course.code == 'CS201' and en.final_grade is None:
                en.mid_term_grade = 16.5
                en.final_grade = 17.0
                en.attendance_score = 18
                en.status = 'completed'
                en.save()

        ExamSchedule.objects.get_or_create(
            course=courses[0],
            semester=semester,
            exam_type='midterm',
            date=today + timedelta(days=14),
            defaults={
                'start_time': time(9, 0),
                'end_time': time(11, 0),
                'location': 'سالن امتحانات ۱',
            },
        )
        ExamSchedule.objects.get_or_create(
            course=courses[1],
            semester=semester,
            exam_type='final',
            date=today + timedelta(days=45),
            defaults={
                'start_time': time(14, 0),
                'end_time': time(16, 0),
                'location': 'سالن امتحانات ۲',
            },
        )

        due = timezone.now() + timedelta(days=7)
        for course, title in [
            (courses[0], 'تمرین فصل ۳'),
            (courses[1], 'پروژه پایگاه داده'),
        ]:
            Assignment.objects.get_or_create(
                course=course,
                semester=semester,
                professor=professor,
                title=title,
                defaults={
                    'description': f'توضیحات {title}',
                    'assignment_type': 'homework' if 'تمرین' in title else 'project',
                    'due_date': due,
                    'max_score': 20,
                    'is_active': True,
                },
            )

        StudentRequest.objects.get_or_create(
            student=student,
            title='درخواست گواهی اشتغال به تحصیل',
            defaults={
                'request_type': 'certificate',
                'description': 'برای ارائه به محل کار',
                'status': 'pending',
            },
        )

        Payment.objects.get_or_create(
            student=student,
            payment_type='tuition',
            amount=8500000,
            semester=semester,
            defaults={
                'description': 'شهریه ترم جاری',
                'status': 'paid',
                'payment_date': timezone.now() - timedelta(days=10),
                'transaction_id': 'DEMO-TX-001',
            },
        )

        self.stdout.write(self.style.SUCCESS(
            'Panel demo data ready.\n'
            '  student: student1 / student123\n'
            '  professor: professor1 / professor123\n'
            '  staff: staff1 / staff123'
        ))
