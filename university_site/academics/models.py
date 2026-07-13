from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class Department(models.Model):
    name = models.CharField(_('نام دانشکده'), max_length=200)
    slug = models.SlugField(unique=True, allow_unicode=True)
    short_description = models.TextField(_('معرفی کوتاه'), blank=True)
    description = models.TextField(_('توضیحات کامل'), blank=True)
    image = models.ImageField(_('تصویر'), upload_to='departments/', blank=True, null=True)
    head = models.CharField(_('رئیس دانشکده'), max_length=200, blank=True)
    established_year = models.CharField(_('سال تأسیس'), max_length=10, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    location = models.CharField(_('محل'), max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('دانشکده')
        verbose_name_plural = _('دانشکده‌ها')
        ordering = ['order']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('academics:department_detail', args=[self.slug])


class Major(models.Model):
    DEGREE_CHOICES = [
        ('associate', 'کاردانی'),
        ('bachelor', 'کارشناسی'),
        ('master', 'کارشناسی ارشد'),
        ('phd', 'دکتری'),
    ]
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='majors', verbose_name=_('دانشکده'))
    name = models.CharField(_('نام رشته'), max_length=200)
    slug = models.SlugField(unique=True, allow_unicode=True)
    degree = models.CharField(_('مقطع تحصیلی'), max_length=20, choices=DEGREE_CHOICES)
    description = models.TextField(_('معرفی رشته'), blank=True)
    job_market = models.TextField(_('بازار کار'), blank=True)
    objectives = models.TextField(_('اهداف'), blank=True)
    curriculum = models.TextField(_('سرفصل دروس'), blank=True)
    total_credits = models.PositiveIntegerField(_('تعداد کل واحد'), default=0)
    capacity = models.PositiveIntegerField(_('ظرفیت'), default=0)
    admission_requirements = models.TextField(_('شرایط پذیرش'), blank=True)
    tuition_fee = models.CharField(_('شهریه'), max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('رشته تحصیلی')
        verbose_name_plural = _('رشته‌های تحصیلی')
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.name} - {self.get_degree_display()}"

    def get_absolute_url(self):
        return reverse('academics:major_detail', args=[self.slug])


class Course(models.Model):
    COURSE_TYPE = [
        ('required', 'اجباری'),
        ('elective', 'اختیاری'),
        ('general', 'عمومی'),
        ('specialized', 'تخصصی'),
    ]
    major = models.ForeignKey(Major, on_delete=models.CASCADE, related_name='courses', verbose_name=_('رشته'))
    name = models.CharField(_('نام درس'), max_length=200)
    code = models.CharField(_('کد درس'), max_length=20, blank=True)
    credits = models.PositiveIntegerField(_('تعداد واحد'), default=3)
    course_type = models.CharField(_('نوع درس'), max_length=20, choices=COURSE_TYPE, default='required')
    prerequisites = models.CharField(_('پیش‌نیاز'), max_length=300, blank=True)
    description = models.TextField(_('توضیحات'), blank=True)
    semester = models.PositiveIntegerField(_('ترم'), default=1)

    class Meta:
        verbose_name = _('درس')
        verbose_name_plural = _('دروس')
        ordering = ['semester', 'name']

    def __str__(self):
        return f"{self.name} ({self.credits} واحد)"


class AcademicCalendar(models.Model):
    SEMESTER_CHOICES = [
        ('fall', 'پاییز'),
        ('spring', 'بهار'),
        ('summer', 'تابستان'),
    ]
    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(_('توضیحات'), blank=True)
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    semester = models.CharField(_('نیم‌سال'), max_length=20, choices=SEMESTER_CHOICES)
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20)
    is_important = models.BooleanField(_('مهم'), default=False)

    class Meta:
        verbose_name = _('تقویم آموزشی')
        verbose_name_plural = _('تقویم آموزشی')
        ordering = ['start_date']

    def __str__(self):
        return f"{self.title} - {self.academic_year}"


class Laboratory(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='labs', verbose_name=_('دانشکده'))
    name = models.CharField(_('نام آزمایشگاه'), max_length=200)
    description = models.TextField(_('توضیحات'), blank=True)
    image = models.ImageField(_('تصویر'), upload_to='labs/', blank=True, null=True)
    supervisor = models.CharField(_('مسئول'), max_length=200, blank=True)
    location = models.CharField(_('محل'), max_length=200, blank=True)
    equipment = models.TextField(_('تجهیزات'), blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('آزمایشگاه')
        verbose_name_plural = _('آزمایشگاه‌ها')

    def __str__(self):
        return self.name


class AcademicGroup(models.Model):
    """گروه آموزشی زیرمجموعه دانشکده"""
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE,
        related_name='groups', verbose_name=_('دانشکده')
    )
    name = models.CharField(_('نام گروه'), max_length=200)
    slug = models.SlugField(unique=True, allow_unicode=True, blank=True)
    head = models.CharField(_('مدیر گروه'), max_length=200, blank=True)
    head_photo = models.ImageField(_('تصویر مدیر گروه'), upload_to='groups/', blank=True, null=True)
    head_email = models.EmailField(_('ایمیل مدیر گروه'), blank=True)
    head_phone = models.CharField(_('تلفن مدیر گروه'), max_length=50, blank=True)
    description = models.TextField(_('معرفی گروه'), blank=True)
    goals = models.TextField(_('اهداف گروه'), blank=True)
    facilities = models.TextField(_('امکانات و تجهیزات'), blank=True)
    research_areas = models.TextField(_('حوزه‌های پژوهشی'), blank=True)
    phone = models.CharField(_('تلفن گروه'), max_length=50, blank=True)
    email = models.EmailField(_('ایمیل گروه'), blank=True)
    location = models.CharField(_('محل'), max_length=200, blank=True)
    established_year = models.CharField(_('سال تأسیس'), max_length=10, blank=True)
    image = models.ImageField(_('تصویر'), upload_to='groups/', blank=True, null=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('گروه آموزشی')
        verbose_name_plural = _('گروه‌های آموزشی')
        ordering = ['department', 'order', 'name']

    def __str__(self):
        return f"{self.name} — {self.department.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('academics:group_detail', args=[self.slug])
