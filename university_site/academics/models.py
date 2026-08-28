import re

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
    head_title = models.CharField(
        _('سمت رئیس دانشکده'), max_length=120, blank=True,
        help_text=_('مثلاً: دانشیار گروه مدیریت صنعتی'))
    head_photo = models.ImageField(
        _('عکس رئیس دانشکده'), upload_to='departments/heads/',
        blank=True, null=True)
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
    # مقاطع رسمی + کدهای قدیمی برای سازگاری داده
    DEGREE_CHOICES = [
        ('associate_cont', 'کاردانی پیوسته'),
        ('bachelor_disc', 'کارشناسی ناپیوسته'),
        ('bachelor_cont', 'کارشناسی پیوسته'),
        ('associate_tech', 'کاردانی فنی'),
        ('master', 'کارشناسی ارشد'),
        # قدیمی (فقط برای رکوردهای قبلی)
        ('associate_disc', 'کاردانی ناپیوسته'),
        ('associate', 'کاردانی'),
        ('bachelor', 'کارشناسی'),
        ('phd', 'دکتری'),
    ]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE,
        related_name='majors', verbose_name=_('دانشکده')
    )
    group = models.ForeignKey(
        'AcademicGroup', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='majors',
        verbose_name=_('گروه آموزشی'),
        help_text=_('گروه آموزشی که این رشته زیر آن نمایش داده می‌شود'),
    )
    name = models.CharField(_('نام رشته'), max_length=200)
    slug = models.SlugField(unique=True, allow_unicode=True)
    degree = models.CharField(_('مقطع تحصیلی'), max_length=20, choices=DEGREE_CHOICES)
    description = models.TextField(_('معرفی رشته'), blank=True)
    job_market = models.TextField(_('بازار کار'), blank=True)
    objectives = models.TextField(_('اهداف'), blank=True)
    curriculum = models.TextField(_('سرفصل دروس'), blank=True)
    curriculum_pdf = models.FileField(
        _('فایل سرفصل (PDF)'),
        upload_to='majors/curriculum/',
        blank=True,
        null=True,
        help_text=_('برنامه درسی / سرفصل PDF این رشته'),
    )
    curriculum_word = models.FileField(
        _('فایل سرفصل (Word)'),
        upload_to='majors/curriculum/word/',
        blank=True,
        null=True,
        help_text=_('نسخه Word سرفصل در صورت وجود'),
    )
    code = models.CharField(
        _('کد رشته'), max_length=20, blank=True, db_index=True,
        help_text=_('کد رسمی وزارت علوم — داوطلب در دفترچهٔ سنجش با همین '
                    'کد رشته را پیدا می‌کند.'))
    total_credits = models.PositiveIntegerField(_('تعداد کل واحد'), default=0)
    internship_hours = models.PositiveIntegerField(
        _('ساعت کارآموزی'), default=0,
        help_text=_('صفر یعنی این رشته کارآموزی ندارد.'))
    capacity = models.PositiveIntegerField(_('ظرفیت'), default=0)
    admission_requirements = models.TextField(_('شرایط پذیرش'), blank=True)
    tuition_fee = models.CharField(_('شهریه'), max_length=200, blank=True)
    order = models.PositiveIntegerField(_('ترتیب نمایش'), default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('رشته تحصیلی')
        verbose_name_plural = _('رشته‌های تحصیلی')
        ordering = ['group', 'degree', 'order', 'name']

    def __str__(self):
        return f"{self.name} - {self.get_degree_display()}"

    def save(self, *args, **kwargs):
        if not (self.slug or '').strip():
            from django.utils.text import slugify
            base = slugify(self.name, allow_unicode=True) or f'major-{self.pk or "new"}'
            slug = base
            n = 2
            while Major.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if not (self.slug or '').strip():
            return reverse('academics:majors')
        return reverse('academics:major_detail', args=[self.slug])

    @property
    def admission_degree(self):
        """کد مقطع رسمی برای فرم پذیرش / فیلتر رشته."""
        from core.degree_map import admission_degree_for_major
        return admission_degree_for_major(self)

    @property
    def current_tuition(self):
        """ساختار شهریه فعال از کاتالوگ یکپارچه."""
        return self.tuition_structures.filter(is_active=True).order_by('-academic_year').first()

    @property
    def tuition_display(self):
        """شهریه با سال تحصیلی شمسی و رقم فارسی.

        سال در پایگاه داده میلادی ذخیره شده («۲۰۲۶-۲۰۲۷») ولی سایت فارسی
        است و کاربر ایرانی «۱۴۰۵-۱۴۰۶» را می‌شناسد. تبدیل اینجا انجام
        می‌شود تا هرجای سایت که این ویژگی را نشان می‌دهد، یکسان باشد.
        """
        from core.jalali import jalali_year_range, to_persian_digits

        ts = self.current_tuition
        if ts:
            amount = to_persian_digits(f'{ts.fixed_fee:,}')
            year = jalali_year_range(ts.academic_year)
            return f'{amount} تومان (ثابت) — سال {year}'
        return self.tuition_fee or '—'


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
    # متن آزاد قدیمی — فقط برای نمایش/سازگاری. منطق روی prereq_courses است.
    prerequisites = models.CharField(
        _('پیش‌نیاز (متن)'), max_length=300, blank=True,
        help_text=_('فقط توضیح نمایشی. برای اعمال واقعی از «دروس پیش‌نیاز» استفاده کنید.'),
    )
    prereq_courses = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='is_prereq_for', verbose_name=_('دروس پیش‌نیاز'),
        help_text=_('دانشجو تا این دروس را پاس نکند نمی‌تواند این درس را بردارد.'),
    )
    coreq_courses = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='is_coreq_for', verbose_name=_('دروس هم‌نیاز'),
        help_text=_('باید هم‌زمان یا پیش از این درس گرفته شده باشند.'),
    )
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
    # هر مرحله به یک قابلیت واقعی پنل دانشجو وصل می‌شود تا کلیک روی آن
    # کاربر را به همان صفحه ببرد — نه یک تصویر بی‌عمل.
    ACTION_CHOICES = [
        ('',                    'بدون لینک'),
        ('registration',        'انتخاب واحد'),
        ('schedule',            'برنامه کلاس'),
        ('payments',            'پرداخت شهریه'),
        ('exams',               'برنامه امتحانات'),
        ('exam_card',           'کارت ورود به جلسه'),
        ('grades',              'نمرات و کارنامه'),
        ('courses',             'دروس من'),
        ('clearance',           'تسویه حساب'),
        ('requests',            'درخواست‌های دانشجویی'),
        ('admissions_apply',    'ثبت درخواست پذیرش'),
        ('admissions_track',    'پیگیری پذیرش'),
        ('tuition_calc',        'محاسبه شهریه'),
        ('external',            'لینک دلخواه (آدرس دستی)'),
    ]
    # نام مسیر جنگو برای هر اقدام — در قالب به URL تبدیل می‌شود
    ACTION_URLS = {
        'registration':     'dashboard:student_registration',
        'schedule':         'dashboard:student_schedule',
        'payments':         'dashboard:student_payments',
        'exams':            'dashboard:student_exams',
        'exam_card':        'dashboard:student_exam_card',
        'grades':           'dashboard:student_grades',
        'courses':          'dashboard:student_courses',
        'clearance':        'dashboard:student_clearance',
        'requests':         'dashboard:student_requests',
        'admissions_apply': 'admissions:apply',
        'admissions_track': 'admissions:track',
        'tuition_calc':     'admissions:tuition_calc',
    }
    TONE_CHOICES = [
        ('gold',   'طلایی (پیش‌فرض)'),
        ('teal',   'فیروزه‌ای'),
        ('violet', 'بنفش'),
        ('rose',   'گلی'),
        ('amber',  'کهربایی'),
        ('sky',    'آبی آسمانی'),
    ]

    title = models.CharField(_('عنوان'), max_length=200)
    description = models.TextField(
        _('توضیحات'), blank=True,
        help_text=_('در باکس تایم‌لاین زیر عنوان نمایش داده می‌شود.'),
    )
    start_date = models.DateField(_('تاریخ شروع'))
    end_date = models.DateField(_('تاریخ پایان'))
    semester = models.CharField(_('نیم‌سال'), max_length=20, choices=SEMESTER_CHOICES)
    academic_year = models.CharField(_('سال تحصیلی'), max_length=20)
    is_important = models.BooleanField(_('مهم'), default=False)

    # ── نمایش و لینک در تایم‌لاین صفحهٔ اصلی ──
    action = models.CharField(
        _('کلیک روی این مرحله کاربر را ببرد به'), max_length=30,
        choices=ACTION_CHOICES, blank=True, default='',
        help_text=_('صفحهٔ مرتبط در پنل دانشجو یا سایت.'),
    )
    external_url = models.CharField(
        _('آدرس دلخواه'), max_length=300, blank=True, default='',
        help_text=_('فقط اگر گزینهٔ «لینک دلخواه» را انتخاب کرده‌اید.'),
    )
    icon = models.CharField(
        _('آیکون'), max_length=60, blank=True, default='',
        help_text=_('کلاس Font Awesome، مثلاً fa-check-square. خالی = خودکار.'),
    )
    tone = models.CharField(
        _('رنگ باکس'), max_length=10, choices=TONE_CHOICES, default='gold',
    )
    bg_color = models.CharField(
        _('رنگ دلخواه زمینه'), max_length=9, blank=True, default='',
        help_text=_(
            'هر رنگی که بخواهید، مثل #1f6f5c. خالی بگذارید تا همان '
            '«رنگ باکس» بالا استفاده شود. رنگ نوشته خودکار روشن یا '
            'تیره می‌شود تا خوانا بماند.'),
    )
    image = models.ImageField(
        _('تصویر مرحله'), upload_to='calendar/', blank=True, null=True,
        help_text=_('اختیاری — پشت باکس این مرحله نمایش داده می‌شود.'),
    )
    order = models.PositiveIntegerField(
        _('ترتیب'), default=0,
        help_text=_('در صورت برابری، تاریخ شروع ملاک است.'),
    )
    is_active = models.BooleanField(_('نمایش در تایم‌لاین'), default=True)

    class Meta:
        verbose_name = _('تقویم آموزشی')
        verbose_name_plural = _('تقویم آموزشی')
        ordering = ['order', 'start_date']

    def __str__(self):
        return f"{self.title} - {self.academic_year}"

    # ── کمکی‌های نمایش ──
    DEFAULT_ICONS = {
        'registration': 'fa-check-square',
        'schedule': 'fa-calendar-alt',
        'payments': 'fa-money-check-alt',
        'exams': 'fa-file-alt',
        'exam_card': 'fa-id-card',
        'grades': 'fa-award',
        'courses': 'fa-book',
        'clearance': 'fa-clipboard-check',
        'requests': 'fa-paper-plane',
        'admissions_apply': 'fa-user-graduate',
        'admissions_track': 'fa-search',
        'tuition_calc': 'fa-calculator',
    }


    # ── رنگ دلخواه زمینه ──
    HEX_PATTERN = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

    @property
    def safe_bg_color(self) -> str:
        """رنگ زمینه، فقط اگر شکل هگز داشته باشد.

        این مقدار داخل صفت style کارت می‌نشیند. هر رشتهٔ دیگری آنجا
        می‌تواند از اعلان بیرون بزند، پس به‌جای فرار دادن، هرچه
        الگو را نداشته باشد دور ریخته می‌شود.
        """
        value = (self.bg_color or '').strip()
        return value if self.HEX_PATTERN.match(value) else ''

    @property
    def bg_is_dark(self) -> bool:
        """آیا زمینهٔ انتخابی تیره است؟

        روشنایی نسبی طبق WCAG حساب می‌شود تا رنگ نوشته خودکار
        برعکسِ زمینه انتخاب شود. بدون این، اولین رنگ تیره‌ای که
        ادمین انتخاب کند متن سرمه‌ای را نامرئی می‌کند — همان اشتباهی
        که یک بار در حالت تیرهٔ سایت افتاد.
        """
        colour = self.safe_bg_color
        if not colour:
            return False
        value = colour.lstrip('#')
        if len(value) == 3:
            value = ''.join(ch * 2 for ch in value)
        channels = []
        for i in (0, 2, 4):
            c = int(value[i:i + 2], 16) / 255
            channels.append(c / 12.92 if c <= 0.03928
                            else ((c + 0.055) / 1.055) ** 2.4)
        luminance = (0.2126 * channels[0] + 0.7152 * channels[1]
                     + 0.0722 * channels[2])
        # ۰٫۳۶ آستانه‌ای است که برای رنگ‌های میانه (سبز و آبی سیر)
        # نتیجهٔ درست می‌دهد؛ ۰٫۵ آن‌ها را روشن حساب می‌کرد.
        return luminance < 0.36

    @property
    def card_style(self) -> str:
        """محتوای صفت style کارت — خالی اگر رنگی انتخاب نشده باشد."""
        colour = self.safe_bg_color
        if not colour:
            return ''
        if self.bg_is_dark:
            ink, soft = '#ffffff', 'rgba(255,255,255,.82)'
        else:
            ink, soft = '#0d2137', '#3c5470'
        return ('--acal-bg:%s;--acal-ink:%s;--acal-ink-soft:%s;'
                '--acal-accent:%s' % (colour, ink, soft, ink))

    @property
    def display_icon(self) -> str:
        if self.icon:
            return self.icon.strip()
        return self.DEFAULT_ICONS.get(self.action, 'fa-circle-dot')

    def get_action_url(self) -> str:
        """آدرس مقصد این مرحله (یا رشتهٔ خالی)."""
        from django.urls import NoReverseMatch, reverse

        if self.action == 'external':
            return (self.external_url or '').strip()
        name = self.ACTION_URLS.get(self.action)
        if not name:
            return ''
        try:
            return reverse(name)
        except NoReverseMatch:
            return ''

    @property
    def is_multi_day(self) -> bool:
        return bool(self.end_date and self.end_date != self.start_date)


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
    # مدیر گروه، از میان اعضای هیئت علمی.
    #
    # پیش از این فقط چهار فیلد متنی بود — نام، عکس، ایمیل، تلفن —
    # یعنی همان استاد دو بار در دیتابیس می‌نشست: یک بار در «اعضای
    # هیئت علمی» و یک بار اینجا. با هر تغییر (ارتقای مرتبه، عکس
    # تازه، ایمیل جدید) یکی به‌روز می‌شد و دیگری کهنه می‌ماند.
    #
    # حالا یک ارجاع است: اطلاعات یک جا ثبت می‌شود و همه‌جا تازه است.
    # فیلدهای متنی می‌مانند تا هم داده‌های قبلی از بین نرود، هم اگر
    # مدیر گروه عضو هیئت علمی نبود بشود دستی نوشتش.
    head_professor = models.ForeignKey(
        'faculty.Professor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='heads_groups',
        verbose_name=_('مدیر گروه (از اعضای هیئت علمی)'),
        help_text=_(
            'با انتخاب استاد، نام و عکس و مرتبه و راه تماسش خودکار '
            'روی صفحهٔ گروه می‌آید. اگر مدیر گروه عضو هیئت علمی نیست، '
            'این را خالی بگذارید و فیلدهای زیر را دستی پر کنید.'))
    head = models.CharField(_('مدیر گروه (دستی)'), max_length=200, blank=True)
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
    # ── تحصیلات تکمیلی (بند ۱۷ سند اصلاحات موسسه) ──
    has_graduate = models.BooleanField(
        _('دارای تحصیلات تکمیلی'), default=False,
        help_text=_('اگر تیک بخورد، زیر منوی «تحصیلات تکمیلی» می‌آید.'))
    graduate_order = models.PositiveIntegerField(
        _('ترتیب در تحصیلات تکمیلی'), default=0,
        help_text=_('ترتیب نمایش در همان زیرمنو؛ عدد کوچک‌تر بالاتر.'))

    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    # ── مدیر گروه: یک منبع، چند نما ────────────────────────────
    # هر ویژگی اول سراغ عضو هیئت علمی می‌رود و اگر نبود، به همان
    # فیلد متنیِ قدیمی برمی‌گردد. پس صفحه‌ها یک چیز صدا می‌زنند و
    # لازم نیست هرکدام خودشان تصمیم بگیرند.
    @property
    def head_name(self) -> str:
        if self.head_professor_id:
            return self.head_professor.get_full_name()
        return self.head or ''

    @property
    def head_image(self):
        if self.head_professor_id and self.head_professor.photo:
            return self.head_professor.photo
        return self.head_photo or None

    @property
    def head_rank(self) -> str:
        """مرتبهٔ علمی — فقط وقتی از رکورد استاد می‌آید."""
        if self.head_professor_id:
            return self.head_professor.get_rank_display()
        return ''

    @property
    def head_page(self) -> str:
        """نشانی صفحهٔ استاد، اگر مدیر گروه عضو هیئت علمی باشد."""
        if not self.head_professor_id:
            return ''
        try:
            return self.head_professor.get_absolute_url()
        except Exception:                          # noqa: BLE001
            return ''

    @property
    def head_contact_email(self) -> str:
        if self.head_professor_id and self.head_professor.email:
            return self.head_professor.email
        return self.head_email or ''

    @property
    def head_contact_phone(self) -> str:
        if self.head_professor_id and self.head_professor.phone:
            return self.head_professor.phone
        return self.head_phone or ''

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
