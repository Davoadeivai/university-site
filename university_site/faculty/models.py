from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from academics.models import Department


class Professor(models.Model):
    RANK_CHOICES = [
        ('instructor', 'مربی'),
        ('assistant', 'استادیار'),
        ('associate', 'دانشیار'),
        ('professor', 'استاد تمام'),
        ('emeritus', 'استاد بازنشسته'),
    ]
    STATUS_CHOICES = [
        ('full_time', 'تمام وقت'),
        ('part_time', 'نیمه وقت'),
        ('visiting', 'مهمان'),
    ]
    first_name = models.CharField(_('نام'), max_length=100)
    last_name = models.CharField(_('نام خانوادگی'), max_length=100)
    slug = models.SlugField(unique=True, allow_unicode=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('دانشکده'), related_name='professors')
    rank = models.CharField(_('مرتبه علمی'), max_length=20, choices=RANK_CHOICES)
    status = models.CharField(_('وضعیت'), max_length=20, choices=STATUS_CHOICES, default='full_time')
    photo = models.ImageField(_('عکس'), upload_to='professors/', blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(_('تلفن'), max_length=50, blank=True)
    office = models.CharField(_('اتاق'), max_length=100, blank=True)
    bio = models.TextField(_('بیوگرافی'), blank=True)
    education = models.TextField(_('سوابق تحصیلی'), blank=True)
    specialization = models.TextField(_('تخصص'), blank=True)
    research_interests = models.TextField(_('زمینه تحقیقاتی'), blank=True)
    office_hours = models.TextField(_('ساعت حضور'), blank=True)
    personal_website = models.URLField(blank=True)
    google_scholar = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    researchgate = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('استاد')
        verbose_name_plural = _('اساتید')
        ordering = ['order', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_absolute_url(self):
        return reverse('faculty:professor_detail', args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(f"{self.first_name}-{self.last_name}", allow_unicode=True)
        super().save(*args, **kwargs)


class Publication(models.Model):
    PUB_TYPE = [
        ('article', 'مقاله'),
        ('book', 'کتاب'),
        ('thesis', 'پایان‌نامه'),
        ('conference', 'کنفرانس'),
        ('report', 'گزارش'),
    ]
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='publications', verbose_name=_('استاد'))
    title = models.CharField(_('عنوان'), max_length=400)
    pub_type = models.CharField(_('نوع'), max_length=20, choices=PUB_TYPE, default='article')
    journal_conference = models.CharField(_('مجله/کنفرانس'), max_length=300, blank=True)
    year = models.PositiveIntegerField(_('سال'))
    doi = models.CharField(_('DOI'), max_length=200, blank=True)
    url = models.URLField(blank=True)
    abstract = models.TextField(_('چکیده'), blank=True)

    class Meta:
        verbose_name = _('انتشار')
        verbose_name_plural = _('انتشارات')
        ordering = ['-year']

    def __str__(self):
        return self.title
