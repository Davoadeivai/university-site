from django.db import models
from django.utils.translation import gettext_lazy as _


class AdmissionInfo(models.Model):
    DEGREE_CHOICES = [
        ('associate', 'کاردانی'),
        ('bachelor', 'کارشناسی'),
        ('master', 'کارشناسی ارشد'),
        ('phd', 'دکتری'),
    ]
    degree = models.CharField(_('مقطع'), max_length=20, choices=DEGREE_CHOICES, unique=True)
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'), blank=True)
    requirements = models.TextField(_('شرایط پذیرش'))
    tuition_info = models.TextField(_('اطلاعات شهریه'), blank=True)
    documents_required = models.TextField(_('مدارک لازم'), blank=True)
    registration_link = models.URLField(_('لینک ثبت‌نام'), blank=True)
    is_active = models.BooleanField(default=True)
    deadline = models.DateField(_('مهلت ثبت‌نام'), blank=True, null=True)

    class Meta:
        verbose_name = _('اطلاعات پذیرش')
        verbose_name_plural = _('اطلاعات پذیرش')

    def __str__(self):
        return f"پذیرش {self.get_degree_display()}"


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('reviewing', 'در حال بررسی'),
        ('accepted', 'پذیرفته شده'),
        ('rejected', 'رد شده'),
        ('waiting', 'لیست انتظار'),
    ]
    DEGREE_CHOICES = [
        ('associate', 'کاردانی'),
        ('bachelor', 'کارشناسی'),
        ('master', 'کارشناسی ارشد'),
        ('phd', 'دکتری'),
    ]
    first_name = models.CharField(_('نام'), max_length=100)
    last_name = models.CharField(_('نام خانوادگی'), max_length=100)
    national_id = models.CharField(_('کد ملی'), max_length=10)
    birth_date = models.DateField(_('تاریخ تولد'))
    phone = models.CharField(_('تلفن'), max_length=15)
    email = models.EmailField()
    address = models.TextField(_('آدرس'))
    desired_major = models.CharField(_('رشته مورد علاقه'), max_length=200)
    degree = models.CharField(_('مقطع'), max_length=20, choices=DEGREE_CHOICES)
    gpa = models.DecimalField(_('معدل'), max_digits=4, decimal_places=2, blank=True, null=True)
    previous_degree = models.CharField(_('مدرک قبلی'), max_length=200, blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(_('یادداشت'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('درخواست پذیرش')
        verbose_name_plural = _('درخواست‌های پذیرش')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_degree_display()}"


class Tuition(models.Model):
    major = models.CharField(_('رشته'), max_length=200)
    degree = models.CharField(_('مقطع'), max_length=50)
    base_fee = models.PositiveIntegerField(_('شهریه پایه (تومان)'))
    per_credit_fee = models.PositiveIntegerField(_('شهریه هر واحد (تومان)'))
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _('شهریه')
        verbose_name_plural = _('شهریه‌ها')

    def __str__(self):
        return f"{self.major} - {self.degree} ({self.academic_year})"
