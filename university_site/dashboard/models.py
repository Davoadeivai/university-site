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
    teaching_assignment = models.ForeignKey(
        'TeachingAssignment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollments',
        verbose_name=_('کلاس / استاد انتخابی'),
    )
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
    """پرداخت‌های سامانه آموزشی (دانشجوی ثبت‌نام‌شده) — جدا از اقساط پذیرش."""
    PAYMENT_TYPE_CHOICES = [
        ('tuition', 'شهریه'),
        ('dorm', 'خوابگاه'),
        ('book', 'کتاب'),
        ('exam', 'امتحان'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('review', 'در انتظار تأیید امور مالی'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('refunded', 'بازگشت داده شده'),
    ]
    STAGE_CHOICES = [
        ('', '—'),
        ('initial', 'قسط اول (ثبت‌نام)'),
        ('mid', 'قسط دوم (میانی)'),
        ('exam_card', 'قسط سوم (کارت ورود به جلسه)'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments', verbose_name=_('دانشجو'))
    payment_type = models.CharField(_('نوع پرداخت'), max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.PositiveIntegerField(_('مبلغ (تومان)'))
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('ترم'))
    description = models.TextField(_('توضیحات'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    installment_no = models.PositiveSmallIntegerField(_('شماره قسط'), default=0, db_index=True)
    installment_stage = models.CharField(
        _('مرحله قسط'), max_length=20, choices=STAGE_CHOICES, blank=True, default='',
    )
    METHOD_CHOICES = [
        ('online', 'پرداخت آنلاین (درگاه)'),
        ('card_to_card', 'کارت‌به‌کارت'),
        ('pos', 'کارت‌خوان / کارتخوان در مؤسسه'),
        ('bank_deposit', 'فیش بانکی / واریز به حساب'),
        ('cash', 'نقدی در امور مالی'),
        ('other', 'سایر'),
    ]
    method = models.CharField(
        _('روش پرداخت'), max_length=20, choices=METHOD_CHOICES, default='online', blank=True,
    )
    due_date = models.DateField(_('سررسید قسط'), null=True, blank=True, db_index=True)
    receipt_file = models.FileField(
        _('فیش / رسید آفلاین'), upload_to='tuition_receipts/', blank=True, null=True,
    )
    receipt_ref = models.CharField(_('شماره پیگیری / مرجع'), max_length=100, blank=True)
    method_notes = models.TextField(_('توضیح روش پرداخت'), blank=True)
    reminder_sent_at = models.DateTimeField(_('آخرین یادآوری پیامکی'), null=True, blank=True)
    exam_barcode = models.CharField(_('بارکد کارت امتحان'), max_length=64, blank=True, db_index=True)
    transaction_id = models.CharField(_('شناسه تراکنش'), max_length=100, blank=True)
    authority = models.CharField(_('کد authority درگاه'), max_length=100, blank=True, db_index=True)
    gateway = models.CharField(_('درگاه'), max_length=20, blank=True, default='')
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('پرداخت سامانه آموزشی')
        verbose_name_plural = _('پرداخت‌های سامانه آموزشی')
        ordering = ['installment_no', '-created_at']

    def __str__(self):
        stage = self.get_installment_stage_display() if self.installment_stage else ''
        base = f"{self.student.get_full_name()} - {self.amount:,} تومان"
        return f"{base} ({stage})" if stage else base

    @property
    def is_exam_gate(self) -> bool:
        return self.installment_stage == 'exam_card'


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


class TuitionInstallmentPlan(models.Model):
    """نسبت و سررسید اقساط شهریه به‌ازای سال تحصیلی (ادمین)."""
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20, unique=True)
    ratio_initial = models.PositiveSmallIntegerField(_('درصد قسط ۱'), default=40)
    ratio_mid = models.PositiveSmallIntegerField(_('درصد قسط ۲'), default=30)
    ratio_exam = models.PositiveSmallIntegerField(_('درصد قسط ۳'), default=30)
    due_days_initial = models.PositiveSmallIntegerField(_('سررسید قسط ۱ (روز از شروع ترم)'), default=7)
    due_days_mid = models.PositiveSmallIntegerField(_('سررسید قسط ۲ (روز از شروع ترم)'), default=60)
    due_days_exam = models.PositiveSmallIntegerField(_('سررسید قسط ۳ (روز از شروع ترم)'), default=100)
    reminder_days_before = models.PositiveSmallIntegerField(_('یادآوری پیامک چند روز قبل'), default=3)
    is_active = models.BooleanField(_('فعال'), default=True)
    notes = models.TextField(_('توضیحات'), blank=True)

    class Meta:
        verbose_name = _('برنامه اقساط شهریه')
        verbose_name_plural = _('برنامه‌های اقساط شهریه')
        ordering = ['-academic_year']

    def __str__(self):
        return f'{self.academic_year} ({self.ratio_initial}/{self.ratio_mid}/{self.ratio_exam})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.ratio_initial + self.ratio_mid + self.ratio_exam != 100:
            raise ValidationError('جمع درصد اقساط باید دقیقاً ۱۰۰ باشد.')

    @property
    def ratios(self):
        return (self.ratio_initial, self.ratio_mid, self.ratio_exam)


class StudentDiscountClaim(models.Model):
    """درخواست/اعمال تخفیف شهریه برای دانشجو (خواهر/برادر، ایثارگری، …)."""
    DISCOUNT_CHOICES = [
        ('sibling', 'تخفیف خواهر / برادر'),
        ('martyr', 'ایثارگری / خانواده شهید'),
        ('veteran', 'جانبازی / ایثارگری'),
        ('talent', 'استعداد درخشان'),
        ('other', 'سایر'),
    ]
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_claims', verbose_name=_('دانشجو'))
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='discount_claims', verbose_name=_('ترم'))
    discount_type = models.CharField(_('نوع تخفیف'), max_length=20, choices=DISCOUNT_CHOICES)
    percent = models.PositiveSmallIntegerField(_('درصد تخفیف'), default=10)
    document = models.FileField(_('مدرک پیوست'), upload_to='tuition_discounts/', blank=True, null=True)
    notes = models.TextField(_('توضیحات دانشجو'), blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(_('یادداشت ادمین'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('تخفیف شهریه دانشجو')
        verbose_name_plural = _('تخفیف‌های شهریه دانشجو')
        ordering = ['-created_at']
        unique_together = ['student', 'semester', 'discount_type']

    def __str__(self):
        return f'{self.student} — {self.get_discount_type_display()} ({self.percent}%)'
