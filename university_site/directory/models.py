"""بانک اطلاعات موسسه — افراد، سرفصل‌های مصوب و منابع بیرونی.

چرا یک اپ جدا
─────────────
داده‌های این اپ از اسناد رسمی موسسه می‌آیند (دفترچهٔ تلفن، فهرست هیات
موسس و امنا، اسامی مدرسین، سرفصل‌های مصوب وزارت). این‌ها با محتوای
تحریریه‌ای سایت فرق دارند: کسی آن‌ها را «می‌نویسد» نه، بلکه از یک سند
بالادستی رونویسی می‌شوند و هر بار که آن سند عوض شود باید یکجا به‌روز
شوند. نگه داشتن‌شان در جدول‌های خودشان یعنی می‌شود کل مجموعه را با یک
دستور دوباره بارگذاری کرد بدون آنکه به محتوای دستیِ بقیهٔ سایت دست بخورد.

نسبت با مدل‌های موجود
──────────────────────
`core.BoardMember` و `faculty.Professor` از قبل هستند و صفحه‌های عمومی
خودشان را دارند. این اپ جایگزین‌شان نمی‌شود؛ فهرست کامل و خام سند را
نگه می‌دارد. برای اعضای هیات که صفحهٔ عمومی دارند، دستور `seed_directory`
همزمان `BoardMember` را هم پر می‌کند تا آن صفحه خالی نماند.
"""
from __future__ import annotations

import os

from django.db import models
from django.utils.translation import gettext_lazy as _


class DirectoryPerson(models.Model):
    """هر کسی که در ساختار موسسه نامی دارد — از رئیس تا مدرس مدعو."""

    CATEGORY_CHOICES = [
        ('staff', _('کارکنان و مسئولان')),
        ('founder', _('هیات موسس')),
        ('trustee', _('هیات امنا')),
        ('faculty', _('اعضای هیات علمی')),
        ('group_head', _('مدیران گروه آموزشی')),
        ('lecturer', _('مدرسین')),
    ]

    DEGREE_CHOICES = [
        ('phd', _('دکتری تخصصی')),
        ('ms', _('کارشناسی ارشد')),
        ('bs', _('کارشناسی')),
        ('other', _('سایر')),
    ]

    # همان فهرستی که پروندهٔ هیئت علمی دارد، تا دو جا دو چیز نگویند.
    RANK_CHOICES = [
        ('instructor', _('مربی')),
        ('assistant', _('استادیار')),
        ('associate', _('دانشیار')),
        ('professor', _('استاد تمام')),
        ('emeritus', _('استاد بازنشسته')),
    ]

    category = models.CharField(
        _('دسته'), max_length=20, choices=CATEGORY_CHOICES, db_index=True)

    # عنوان افتخاری جدا از نام نگه داشته می‌شود تا مرتب‌سازی الفبایی
    # روی «دکتر» گیر نکند و همهٔ دکترها کنار هم نیفتند.
    honorific = models.CharField(
        _('پیشوند'), max_length=40, blank=True,
        help_text=_('مثلاً: دکتر، مهندس، حجت‌الاسلام'))
    first_name = models.CharField(_('نام'), max_length=100, blank=True)
    last_name = models.CharField(_('نام خانوادگی'), max_length=100, blank=True)
    full_name = models.CharField(
        _('نام و نام خانوادگی'), max_length=200,
        help_text=_('اگر خالی بماند از نام و نام خانوادگی ساخته می‌شود.'))

    position = models.CharField(_('سمت'), max_length=300, blank=True)
    field_of_study = models.CharField(_('رشته تحصیلی'), max_length=200, blank=True)
    degree = models.CharField(
        _('مدرک تحصیلی'), max_length=20, choices=DEGREE_CHOICES, blank=True)
    # مرتبهٔ علمی، صریح.
    #
    # سند موسسه فقط مدرک داشت، پس مرتبه از مدرک حدس زده می‌شد —
    # دکتری یعنی استادیار. برای بیشتر افراد درست بود و برای کسی که
    # دانشیار یا استاد تمام است غلط، و هیچ کادری هم برای اصلاحش
    # نبود. خالی یعنی «همان حدس»؛ پرکردنش یعنی «این حکم است».
    academic_rank = models.CharField(
        _('مرتبه علمی'), max_length=20, choices=RANK_CHOICES, blank=True,
        help_text=_('اگر خالی بماند از مدرک تحصیلی حدس زده می‌شود '
                    '(دکتری → استادیار). برای دانشیار و استاد تمام '
                    'حتماً پرش کنید.'))

    extension = models.CharField(
        _('شماره داخلی'), max_length=20, blank=True,
        help_text=_('فقط عدد داخلی، مثلاً ۱۱۵'))
    phone = models.CharField(_('تلفن مستقیم'), max_length=50, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    photo = models.ImageField(
        _('تصویر'), upload_to='directory/people/', blank=True, null=True)

    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('فرد')
        verbose_name_plural = _('افراد موسسه')
        ordering = ['category', 'order', 'last_name', 'full_name']
        constraints = [
            # یک نفر در یک دسته فقط یک بار. بدون این، هر بار اجرای
            # seed_directory ردیف‌ها دوباره ساخته می‌شدند.
            models.UniqueConstraint(
                fields=['category', 'full_name'],
                name='directory_person_unique_per_category',
            ),
        ]
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self) -> str:
        return '%s — %s' % (self.get_category_display(), self.display_name)

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = ('%s %s' % (self.first_name, self.last_name)).strip()
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        """نام همراه پیشوند — چیزی که روی سایت دیده می‌شود."""
        return ('%s %s' % (self.honorific, self.full_name)).strip()

    @property
    def contact_line(self) -> str:
        """تلفن مستقیم یا داخلی، هرکدام که پر باشد."""
        if self.phone:
            return self.phone
        return ('داخلی %s' % self.extension) if self.extension else ''


class CurriculumDocument(models.Model):
    """سرفصل مصوب یک رشته — فایل PDF ابلاغی وزارت علوم."""

    LEVEL_CHOICES = [
        ('associate_cont', _('کاردانی پیوسته')),
        ('associate_disc', _('کاردانی ناپیوسته')),
        ('bachelor_cont', _('کارشناسی پیوسته')),
        ('bachelor_disc', _('کارشناسی ناپیوسته')),
        ('master', _('کارشناسی ارشد')),
        ('other', _('سایر')),
    ]

    title = models.CharField(_('عنوان رشته'), max_length=300)
    level = models.CharField(
        _('مقطع'), max_length=20, choices=LEVEL_CHOICES, default='other',
        db_index=True)
    major = models.ForeignKey(
        'academics.Major', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='curriculum_documents', verbose_name=_('رشته مرتبط'),
        help_text=_('اختیاری — برای پیوند دادن به صفحهٔ رشته'))

    file = models.FileField(_('فایل PDF'), upload_to='curricula/')
    # اندازه در ذخیره حساب می‌شود؛ خواندن اندازه از استوریج در هر بار
    # رندر فهرست یعنی یک I/O به ازای هر ردیف.
    file_size = models.PositiveIntegerField(_('حجم (بایت)'), default=0, editable=False)

    approved_on = models.CharField(
        _('تاریخ تصویب'), max_length=30, blank=True,
        help_text=_('همان‌طور که روی سند آمده، مثلاً ۱۴۰۰/۱۰/۱۵'))
    note = models.CharField(_('توضیح'), max_length=300, blank=True)

    download_count = models.PositiveIntegerField(
        _('تعداد دانلود'), default=0, editable=False)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('سرفصل مصوب')
        verbose_name_plural = _('سرفصل‌های مصوب رشته‌ها')
        ordering = ['level', 'order', 'title']
        constraints = [
            # تاریخ تصویب بخشی از کلید است: یک رشته ممکن است چند
            # بازنگری داشته باشد («مکانیک خودرو» مصوب ۱۳۹۸ و نسخهٔ
            # بی‌تاریخ). بدون تاریخ در کلید، ایمپورت نسخهٔ دوم روی
            # نسخهٔ اول می‌نوشت و یکی از دو سند گم می‌شد.
            models.UniqueConstraint(
                fields=['level', 'title', 'approved_on'],
                name='directory_curriculum_unique_per_level',
            ),
        ]

    def __str__(self) -> str:
        return '%s — %s' % (self.get_level_display(), self.title)

    def save(self, *args, **kwargs):
        if self.file:
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                # فایل هنوز روی استوریج نیست یا دسترسی ندارد؛ اندازه
                # نباید جلوی ذخیرهٔ رکورد را بگیرد.
                self.file_size = 0
        super().save(*args, **kwargs)

    @property
    def size_display(self) -> str:
        if not self.file_size:
            return ''
        mb = self.file_size / 1048576
        if mb >= 1:
            return '%.1f مگابایت' % mb
        return '%.0f کیلوبایت' % (self.file_size / 1024)

    @property
    def filename(self) -> str:
        return os.path.basename(self.file.name) if self.file else ''


class ExternalResource(models.Model):
    """پایگاه‌ها و سامانه‌های بیرونی که کتابخانه به آن‌ها ارجاع می‌دهد."""

    CATEGORY_CHOICES = [
        ('database', _('پایگاه داده و منابع لاتین')),
        ('journal', _('نشریات')),
        ('thesis', _('پایان‌نامه‌ها')),
        ('other', _('سایر')),
    ]

    title = models.CharField(_('عنوان'), max_length=200)
    url = models.URLField(_('نشانی'), max_length=500)
    category = models.CharField(
        _('دسته'), max_length=20, choices=CATEGORY_CHOICES, default='other')
    description = models.CharField(_('توضیح'), max_length=300, blank=True)
    icon = models.CharField(
        _('آیکون'), max_length=60, default='fas fa-database', blank=True)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('منبع بیرونی')
        verbose_name_plural = _('منابع و پایگاه‌های بیرونی')
        ordering = ['category', 'order', 'title']
        constraints = [
            models.UniqueConstraint(
                fields=['url'], name='directory_resource_unique_url'),
        ]

    def __str__(self) -> str:
        return self.title
