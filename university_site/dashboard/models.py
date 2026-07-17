from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from academics.models import Major, Course, Department


class Semester(models.Model):
    SEMESTER_CHOICES = [
        ('fall', 'پاییز'),
        ('spring', 'بهار'),
        ('summer', 'تابستان'),
    ]
    name = models.CharField(_('نام ترم'), max_length=100)
    semester_type = models.CharField(_('نوع ترم'), max_length=20, choices=SEMESTER_CHOICES)
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20)
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    is_active = models.BooleanField(_('فعال'), default=False)
    registration_open = models.BooleanField(_('ثبت‌نام باز'), default=False)

    class Meta:
        verbose_name = _('ترم')
        verbose_name_plural = _('ترم‌ها')
        ordering = ['-academic_year', '-start_date']

    def __str__(self):
        return f"{self.name} - {self.academic_year}"


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('registered', 'ثبت‌نام شده'),
        ('in_progress', 'در حال گذراندن'),
        ('completed', 'تکمیل شده'),
        ('dropped', 'حذف شده'),
        ('failed', 'مردود'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('دانشجو'))
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='enrollments', verbose_name=_('ترم'))
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='registered')
    mid_term_grade = models.DecimalField(_('نمره میان‌ترم'), max_digits=5, decimal_places=2, null=True, blank=True)
    final_grade = models.DecimalField(_('نمره نهایی'), max_digits=5, decimal_places=2, null=True, blank=True)
    attendance_score = models.DecimalField(_('نمره حضور'), max_digits=5, decimal_places=2, null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('ثبت‌نام درس')
        verbose_name_plural = _('ثبت‌نام دروس')
        unique_together = ['student', 'course', 'semester']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.course.name}"


class TeachingAssignment(models.Model):
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_assignments', verbose_name=_('استاد'))
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='teaching_assignments', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='teaching_assignments', verbose_name=_('ترم'))
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('دانشکده'))
    class_schedule = models.TextField(_('برنامه کلاس'), blank=True)
    classroom = models.CharField(_('کلاس'), max_length=50, blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('تخصیص تدریس')
        verbose_name_plural = _('تخصیص‌های تدریس')
        unique_together = ['professor', 'course', 'semester']

    def __str__(self):
        return f"{self.professor.get_full_name()} - {self.course.name}"


class StudentRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('certificate', 'گواهی'),
        ('transcript', 'کارنامه'),
        ('recommendation', 'معرفی‌نامه'),
        ('leave', 'مرخصی'),
        ('extension', 'تمدید'),
        ('complaint', 'شکایت'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('processing', 'در حال بررسی'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests', verbose_name=_('دانشجو'))
    request_type = models.CharField(_('نوع درخواست'), max_length=20, choices=REQUEST_TYPE_CHOICES)
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'))
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    response = models.TextField(_('پاسخ'), blank=True)
    file = models.FileField(_('فایل'), upload_to='requests/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('درخواست دانشجویی')
        verbose_name_plural = _('درخواست‌های دانشجویی')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.title}"


class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('tuition', 'شهریه'),
        ('dorm', 'خوابگاه'),
        ('book', 'کتاب'),
        ('exam', 'امتحان'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('refunded', 'بازگشت داده شده'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments', verbose_name=_('دانشجو'))
    payment_type = models.CharField(_('نوع پرداخت'), max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.PositiveIntegerField(_('مبلغ (تومان)'))
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('ترم'))
    description = models.TextField(_('توضیحات'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(_('شناسه تراکنش'), max_length=100, blank=True)
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('پرداخت')
        verbose_name_plural = _('پرداخت‌ها')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.amount:,} تومان"


class ExamSchedule(models.Model):
    EXAM_TYPE_CHOICES = [
        ('midterm', 'میان‌ترم'),
        ('final', 'پایان‌ترم'),
        ('makeup', 'امتحان جایگزین'),
        ('practical', 'امتحان عملی'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='exams', verbose_name=_('ترم'))
    exam_type = models.CharField(_('نوع امتحان'), max_length=20, choices=EXAM_TYPE_CHOICES)
    date = models.DateField(_('تاریخ'))
    start_time = models.TimeField(_('ساعت شروع'))
    end_time = models.TimeField(_('ساعت پایان'))
    location = models.CharField(_('مکان'), max_length=100)
    instructions = models.TextField(_('دستورالعمل'), blank=True)

    class Meta:
        verbose_name = _('برنامه امتحان')
        verbose_name_plural = _('برنامه امتحانات')
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.course.name} - {self.get_exam_type_display()}"


class Assignment(models.Model):
    ASSIGNMENT_TYPE_CHOICES = [
        ('homework', 'تکلیف'),
        ('project', 'پروژه'),
        ('quiz', 'کوییز'),
        ('presentation', 'ارائه'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('درس'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('ترم'))
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('استاد'))
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'))
    assignment_type = models.CharField(_('نوع'), max_length=20, choices=ASSIGNMENT_TYPE_CHOICES)
    due_date = models.DateTimeField(_('مهلت تحویل'))
    max_score = models.PositiveIntegerField(_('امتیاز کل'), default=100)
    file = models.FileField(_('فایل'), upload_to='assignments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('تکلیف')
        verbose_name_plural = _('تکالیف')
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'تحویل داده شده'),
        ('graded', 'نمره داده شده'),
        ('late', 'تاخیری'),
        ('rejected', 'رد شده'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name=_('تکلیف'))
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name=_('دانشجو'))
    file = models.FileField(_('فایل'), upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(_('نمره'), max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(_('بازخورد'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='submitted')

    class Meta:
        verbose_name = _('تحویل تکلیف')
        verbose_name_plural = _('تحویل تکالیف')
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assignment.title}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('late', 'تاخیر'),
        ('excused', 'مرخصی'),
    ]
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='attendance', verbose_name=_('ثبت‌نام'))
    date = models.DateField(_('تاریخ'))
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(_('یادداشت'), blank=True)

    class Meta:
        verbose_name = _('حضور و غیاب')
        verbose_name_plural = _('حضور و غیاب')
        unique_together = ['enrollment', 'date']

    def __str__(self):
        return f"{self.enrollment.student.get_full_name()} - {self.date}"
