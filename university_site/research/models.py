from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class ResearchProject(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'در حال اجرا'),
        ('completed', 'تکمیل شده'),
        ('pending', 'در انتظار'),
    ]
    title = models.CharField(_('عنوان پروژه'), max_length=300)
    researcher = models.CharField(_('محقق'), max_length=200)
    description = models.TextField(_('توضیحات'))
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'), blank=True, null=True)
    budget = models.DecimalField(_('بودجه'), max_digits=15, decimal_places=0, blank=True, null=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='ongoing')
    is_featured = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('پروژه پژوهشی')
        verbose_name_plural = _('پروژه‌های پژوهشی')
        ordering = ['-start_date']

    def __str__(self):
        return self.title


class Journal(models.Model):
    CATEGORY_CHOICES = [
        ('scientific', _('نشریه‌های علمی - پژوهشی')),
        ('online_sub', _('نشریات دارای اشتراک on-line')),
        ('other', _('سایر')),
    ]
    title = models.CharField(_('عنوان مجله'), max_length=300)
    slug = models.SlugField(unique=True, allow_unicode=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        _('دسته'), max_length=20, choices=CATEGORY_CHOICES, default='scientific',
    )
    issn = models.CharField(_('ISSN'), max_length=20, blank=True)
    website = models.URLField(blank=True)
    cover = models.ImageField(upload_to='journals/', blank=True, null=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('مجله علمی')
        verbose_name_plural = _('مجلات علمی')
        ordering = ['category', 'order', 'title']

    def __str__(self):
        return self.title


class Thesis(models.Model):
    DEGREE_CHOICES = [('master', 'کارشناسی ارشد'), ('phd', 'دکتری')]
    title = models.CharField(_('عنوان پایان‌نامه'), max_length=400)
    author = models.CharField(_('نویسنده'), max_length=200)
    supervisor = models.CharField(_('استاد راهنما'), max_length=200)
    department = models.CharField(_('دانشکده'), max_length=200, blank=True)
    degree = models.CharField(_('مقطع'), max_length=10, choices=DEGREE_CHOICES, default='master')
    year = models.PositiveIntegerField(_('سال'))
    abstract = models.TextField(_('چکیده'))
    keywords = models.CharField(_('کلیدواژه‌ها'), max_length=300, blank=True)
    file = models.FileField(_('فایل'), upload_to='theses/', blank=True, null=True)

    class Meta:
        verbose_name = _('پایان‌نامه')
        verbose_name_plural = _('پایان‌نامه‌ها')
        ordering = ['-year']

    def __str__(self):
        return self.title


class Conference(models.Model):
    title = models.CharField(_('عنوان همایش'), max_length=300)
    description = models.TextField(blank=True)
    date = models.DateField()
    location = models.CharField(max_length=200, blank=True)
    organizer = models.CharField(_('برگزارکننده'), max_length=200, blank=True)
    website = models.URLField(blank=True)
    image = models.ImageField(upload_to='conferences/', blank=True, null=True)
    is_upcoming = models.BooleanField(_('آینده'), default=True)

    class Meta:
        verbose_name = _('همایش')
        verbose_name_plural = _('همایش‌ها')
        ordering = ['-date']

    def __str__(self):
        return self.title


class IndustryPartnership(models.Model):
    company_name = models.CharField(_('نام شرکت'), max_length=200)
    description = models.TextField(_('توضیحات'), blank=True)
    logo = models.ImageField(_('لوگو'), upload_to='partners/', blank=True, null=True)
    website = models.URLField(_('وب‌سایت'), blank=True)
    partnership_type = models.CharField(_('نوع همکاری'), max_length=200, blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('همکاری صنعتی')
        verbose_name_plural = _('همکاری‌های صنعتی')

    def __str__(self):
        return self.company_name
