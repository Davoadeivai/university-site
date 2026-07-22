from django.db import models
from django.utils.translation import gettext_lazy as _


class Book(models.Model):
    title = models.CharField(_('عنوان'), max_length=300)
    author = models.CharField(_('نویسنده'), max_length=200)
    translator = models.CharField(_('مترجم'), max_length=200, blank=True)
    publisher = models.CharField(_('ناشر'), max_length=200, blank=True)
    year = models.PositiveIntegerField(_('سال انتشار'))
    isbn = models.CharField(_('شابک'), max_length=50, blank=True)
    subject = models.CharField(_('موضوع'), max_length=200, blank=True)
    language = models.CharField(_('زبان'), max_length=50, default='فارسی')
    cover = models.ImageField(_('جلد'), upload_to='books/', blank=True, null=True)
    description = models.TextField(_('توضیحات'), blank=True)
    copies_available = models.PositiveIntegerField(_('تعداد موجود'), default=1)
    location = models.CharField(_('محل نگهداری'), max_length=100, blank=True)
    is_available = models.BooleanField(_('موجود'), default=True)

    class Meta:
        verbose_name = _('کتاب')
        verbose_name_plural = _('کتاب‌ها')
        ordering = ['title']

    def __str__(self):
        return f"{self.title} - {self.author}"


class Article(models.Model):
    SECTION_CHOICES = [
        ('general', _('عمومی')),
        ('faculty', _('مقالات اعضای هیات علمی')),
        ('conference', _('بانک مقالات همایش‌ها')),
    ]
    title = models.CharField(_('عنوان مقاله'), max_length=400)
    authors = models.CharField(_('نویسندگان'), max_length=400)
    journal = models.CharField(_('مجله'), max_length=200, blank=True)
    year = models.PositiveIntegerField()
    doi = models.CharField(max_length=200, blank=True)
    keywords = models.CharField(_('کلیدواژه'), max_length=300, blank=True)
    abstract = models.TextField(_('چکیده'), blank=True)
    section = models.CharField(
        _('بخش بانک علمی'), max_length=20, choices=SECTION_CHOICES, default='general',
    )
    file = models.FileField(_('فایل'), upload_to='articles/', blank=True, null=True)
    url = models.URLField(blank=True)

    class Meta:
        verbose_name = _('مقاله')
        verbose_name_plural = _('مقالات')
        ordering = ['-year']

    def __str__(self):
        return self.title


class LibraryMembership(models.Model):
    STATUS_CHOICES = [('active', 'فعال'), ('inactive', 'غیرفعال'), ('pending', 'در انتظار')]
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=200)
    student_id = models.CharField(_('شماره دانشجویی'), max_length=50, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = _('عضویت کتابخانه')
        verbose_name_plural = _('اعضای کتابخانه')

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"
