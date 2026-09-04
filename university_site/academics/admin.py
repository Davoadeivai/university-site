from django import forms
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.admin_jalali import JalaliAdminMixin
from core.jalali_forms import JalaliAdminFormMixin
from core.jalali import format_jalali_date

from .models import Department, Major, Course, AcademicCalendar, Laboratory, AcademicGroup


class MajorInline(admin.TabularInline):
    """رشته‌های داخل صفحه دانشکده"""
    model = Major
    fk_name = 'department'
    extra = 0
    fields = ['name', 'group', 'degree', 'order', 'capacity', 'is_active']
    show_change_link = True
    autocomplete_fields = ['group']


class GroupMajorInline(admin.TabularInline):
    """رشته‌های داخل صفحه گروه آموزشی — قابل ویرایش مستقیم"""
    model = Major
    fk_name = 'group'
    extra = 1
    fields = ['name', 'degree', 'order', 'capacity', 'is_active', 'department']
    show_change_link = True
    verbose_name = 'رشته'
    verbose_name_plural = 'رشته‌ها و مقاطع این گروه'


class LaboratoryInline(admin.TabularInline):
    model = Laboratory
    extra = 0
    fields = ['name', 'supervisor', 'location', 'is_active']


class AcademicGroupInline(admin.TabularInline):
    """نمایش گروه‌های آموزشی داخل صفحه دانشکده"""
    model = AcademicGroup
    extra = 1
    fields = ['name', 'head', 'phone', 'order', 'is_active']
    show_change_link = True


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ['name', 'head', 'groups_count', 'majors_count', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter   = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines       = [AcademicGroupInline, MajorInline, LaboratoryInline]
    search_fields = ['name', 'head']
    readonly_fields = ['groups_count', 'majors_count']

    @admin.display(description='تعداد گروه‌ها')
    def groups_count(self, obj):
        n = obj.groups.filter(is_active=True).count()
        return format_html('<span style="color:#2563eb;font-weight:600;">{}</span>', n)

    @admin.display(description='تعداد رشته‌ها')
    def majors_count(self, obj):
        n = obj.majors.filter(is_active=True).count()
        return format_html('<span style="color:#16a34a;font-weight:600;">{}</span>', n)


class CourseInline(admin.TabularInline):
    model = Course
    extra = 0
    fields = ['name', 'code', 'credits', 'course_type', 'semester']


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display    = ['name', 'group', 'department', 'degree', 'enrollment_count', 'order', 'capacity', 'is_active']
    list_filter     = ['degree', 'group', 'department', 'is_active']
    list_editable   = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines         = [CourseInline]
    search_fields   = ['name', 'description']
    autocomplete_fields = ['group', 'department']
    list_select_related = ('group', 'department')
    readonly_fields = ['enrollment_count', 'enrollment_summary']
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'slug', 'department', 'group', 'degree', 'order', 'is_active')
        }),
        ('محتوا', {
            'fields': (
                'description', 'objectives', 'job_market', 'curriculum',
                'curriculum_pdf', 'curriculum_word', 'admission_requirements',
            )
        }),
        ('ظرفیت و شهریه', {
            'fields': ('total_credits', 'capacity', 'tuition_fee')
        }),
        ('انتخاب‌واحد ترم فعال', {
            'fields': ('enrollment_count', 'enrollment_summary'),
            'classes': ('collapse',),
            'description': 'تعداد و وضعیت انتخاب‌واحد دانشجویان این رشته در ترم جاری.',
        }),
    )

    def get_queryset(self, request):
        from dashboard.models import Enrollment, Semester
        active = Semester.objects.filter(is_active=True).first()
        qs = super().get_queryset(request)
        if active:
            qs = qs.annotate(
                _enroll_active=Count(
                    'courses__enrollments',
                    filter=Q(courses__enrollments__semester=active)
                           & ~Q(courses__enrollments__status='dropped'),
                    distinct=True,
                )
            )
        else:
            qs = qs.annotate(_enroll_active=Count('id', distinct=True) * 0)
        return qs

    @admin.display(description='ثبت‌نام ترم فعال', ordering='_enroll_active')
    def enrollment_count(self, obj):
        from dashboard.models import Enrollment, Semester
        active = Semester.objects.filter(is_active=True).first()
        if not active:
            return '—'
        n = Enrollment.objects.filter(
            course__major=obj, semester=active
        ).exclude(status='dropped').count()
        color = '#16a34a' if n > 0 else '#94a3b8'
        return format_html('<span style="color:{};font-weight:600;">{} نفر</span>', color, n)

    @admin.display(description='جزئیات انتخاب‌واحد')
    def enrollment_summary(self, obj):
        from dashboard.models import Enrollment, Semester
        active = Semester.objects.filter(is_active=True).first()
        if not active:
            return 'ترم فعالی تعریف نشده.'
        rows = (
            Enrollment.objects
            .filter(course__major=obj, semester=active)
            .exclude(status='dropped')
            .select_related('student', 'course')
            .order_by('course__semester', 'course__name', 'student__last_name')
        )
        if not rows:
            return format_html('<span style="color:#94a3b8;">هیچ دانشجویی در ترم فعال ثبت‌نام نکرده.</span>')
        status_colors = {
            'registered': '#3b82f6', 'in_progress': '#06b6d4',
            'completed': '#16a34a', 'failed': '#f59e0b',
        }
        html = (
            '<table style="font-size:12px;border-collapse:collapse;width:100%;">'
            '<thead><tr style="background:#f1f5f9;">'
            '<th style="padding:4px 8px;text-align:right;">دانشجو</th>'
            '<th style="padding:4px 8px;text-align:right;">درس</th>'
            '<th style="padding:4px 8px;text-align:right;">وضعیت</th>'
            '</tr></thead><tbody>'
        )
        for e in rows:
            color = status_colors.get(e.status, '#64748b')
            html += (
                f'<tr style="border-bottom:1px solid #e5e7eb;">'
                f'<td style="padding:3px 8px;">{e.student.get_full_name() or e.student.username}</td>'
                f'<td style="padding:3px 8px;">{e.course.name}</td>'
                f'<td style="padding:3px 8px;">'
                f'<span style="background:{color};color:#fff;padding:1px 6px;border-radius:6px;">'
                f'{e.get_status_display()}</span></td></tr>'
            )
        html += '</tbody></table>'
        return format_html('{}', mark_safe(html))


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'major', 'credits', 'course_type', 'semester']
    list_filter = ['course_type', 'semester', 'major__degree', 'major']
    search_fields = ['name', 'code', 'major__name', 'prerequisites']
    autocomplete_fields = ['major']
    list_select_related = ('major',)
    filter_horizontal = ['prereq_courses', 'coreq_courses']
    fieldsets = (
        ('اطلاعات درس', {
            'fields': (
                'major', 'name', 'code', 'credits', 'course_type', 'semester',
                'prereq_courses', 'coreq_courses', 'prerequisites',
            )
        }),
        ('توضیحات', {
            'fields': ('description',),
        }),
    )


@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(JalaliAdminFormMixin, JalaliAdminMixin, admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """انتخابگر رنگ مرورگر برای زمینهٔ دلخواه."""
        if db_field.name == 'bg_color':
            kwargs['widget'] = forms.TextInput(attrs={
                'type': 'color',
                'style': 'width:70px;height:38px;padding:2px;',
            })
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    list_display = [
        'title', 'step_preview', 'semester', 'academic_year_jalali',
        'start_date_jalali', 'end_date_jalali',
        'action_link', 'order', 'is_important', 'is_active',
    ]
    list_filter = ['is_active', 'semester', 'academic_year', 'is_important', 'action', 'tone']
    list_editable = ['order', 'is_important', 'is_active']
    search_fields = ['title', 'description', 'academic_year']
    fieldsets = (
        ('مرحله', {
            'fields': ('title', 'description'),
            'description': (
                'این مراحل در <strong>تایم‌لاین صفحهٔ اصلی</strong> نمایش داده می‌شوند. '
                'وضعیت هر مرحله (گذشته / در جریان / بعدی) خودکار از تاریخ محاسبه می‌شود.'
            ),
        }),
        ('زمان‌بندی', {
            'fields': (
                'start_date',
                'end_date',
                ('semester', 'academic_year'),
            ),
            'description': (
                'تاریخ‌ها را <strong>شمسی</strong> بنویسید — مثلاً '
                '<code>۱۴۰۵/۰۶/۳۱</code>. ارقام فارسی یا انگلیسی، هر دو قبول است. '
                'برای مرحلهٔ یک‌روزه، تاریخ پایان را برابر تاریخ شروع بگذارید.'
            ),
        }),
        ('کلیک و مقصد', {
            'fields': ('action', 'external_url'),
            'description': (
                'با انتخاب یک مورد، کلیک روی این مرحله در تایم‌لاین کاربر را به همان '
                'صفحهٔ پنل دانشجو می‌برد. «بدون لینک» یعنی مرحله فقط نمایشی است.'
            ),
        }),
        ('ظاهر', {
            'fields': ('icon', 'tone', 'bg_color', 'image', 'order'),
            'description': (
                'آیکون را از <a href="https://fontawesome.com/search?o=r&m=free" '
                'target="_blank" rel="noopener">Font Awesome</a> بردارید '
                '(مثلاً <code>fa-check-square</code>). خالی = آیکون خودکار بر اساس مقصد.'
                '<br><b>رنگ باکس</b> شش رنگ آماده است و روی نیم‌دایره و '
                'قاب اثر می‌گذارد. <b>رنگ دلخواه زمینه</b> هر رنگی را '
                'می‌پذیرد و کل زمینهٔ کارت را پر می‌کند؛ رنگ نوشته خودکار '
                'روشن یا تیره می‌شود تا خوانا بماند.'
            ),
        }),
        ('نمایش', {'fields': ('is_important', 'is_active')}),
    )

    # آینه‌های فقط‌خواندنیِ شمسی حذف شدند: حالا خودِ فیلد ورودی شمسی
    # است، پس نمایش دوبارهٔ همان تاریخ کنارش فقط فرم را شلوغ می‌کرد.

    @admin.display(description='نما')
    def step_preview(self, obj):
        from core.models import HomeFeature  # noqa: F401  (رنگ‌ها هم‌خوان بمانند)
        tones = {
            'gold': '#c9a24c', 'teal': '#0d9488', 'violet': '#7c3aed',
            'rose': '#e11d48', 'amber': '#d97706', 'sky': '#0284c7',
        }
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;">'
            '<i class="fas {}" style="color:{};font-size:16px;"></i>'
            '<span style="width:10px;height:10px;border-radius:50%;background:{};'
            'display:inline-block;"></span></span>',
            obj.display_icon, tones.get(obj.tone, '#c9a24c'), tones.get(obj.tone, '#c9a24c'),
        )

    @admin.display(description='مقصد کلیک')
    def action_link(self, obj):
        if not obj.action:
            return format_html('<span style="color:#94a3b8;">—</span>')
        url = obj.get_action_url()
        label = obj.get_action_display()
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, label)
        return format_html('<span style="color:#dc2626;">{} (آدرس نامعتبر)</span>', label)


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'supervisor', 'location', 'is_active']
    list_filter  = ['department', 'is_active']
    search_fields = ['name', 'supervisor', 'equipment']
    list_select_related = ('department',)


@admin.register(AcademicGroup)
class AcademicGroupAdmin(admin.ModelAdmin):
    # پیشوند در همین فهرست قابل ویرایش است: افزودن «دکتر» به یازده
    # گروه نباید یازده بار باز و بسته کردن فرم باشد.
    list_display        = ['name', 'department', 'head_display',
                           'head_honorific', 'majors_count',
                           'has_graduate', 'order', 'is_active']
    list_editable       = ['head_honorific', 'has_graduate', 'order',
                           'is_active']
    list_filter         = ['department', 'is_active', 'has_graduate']
    search_fields       = ['name', 'head', 'head_professor__first_name',
                           'head_professor__last_name', 'description',
                           'research_areas']
    autocomplete_fields = ['head_professor']
    list_select_related = ('department', 'head_professor')
    prepopulated_fields = {'slug': ('name',)}
    inlines             = [GroupMajorInline]

    @admin.display(description='مدیر گروه', ordering='head')
    def head_display(self, obj):
        """نام مدیر، از هر جا که آمده — با نشانهٔ اینکه پیوند خورده یا نه."""
        from django.utils.html import format_html

        if obj.head_professor_id:
            return format_html(
                '<span style="color:#1f7a5c;font-weight:600;">{}</span>',
                obj.head_name)
        if obj.head:
            return format_html(
                '<span style="color:#8a6412;" title="دستی نوشته شده، به '
                'پروندهٔ هیئت علمی وصل نیست">{}</span>', obj.head_name)
        return format_html('<span style="color:#b3261e;">— ثبت نشده</span>')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('department', 'name', 'slug', 'order', 'is_active', 'image'),
            'description': 'برای ویرایش رشته‌های هر مقطع، از جدول پایین صفحه («رشته‌ها و مقاطع این گروه») استفاده کنید.',
        }),
        ('مدیر گروه', {
            'fields': ('head_honorific', 'head_professor', 'head',
                       'head_photo', 'head_email', 'head_phone'),
            'description': (
                '<b>پیشوند</b> («دکتر»، «مهندس») همیشه اثر دارد — چه نام '
                'از پروندهٔ هیئت علمی بیاید، چه دستی نوشته شده باشد.<br>'
                '<b>روش درست برای نام:</b> استاد را از فهرست «مدیر گروه '
                '(از اعضای هیئت علمی)» انتخاب کنید — نام، عکس، مرتبهٔ '
                'علمی و راه تماسش خودکار روی صفحهٔ گروه می‌آید و با هر '
                'تغییر در پروندهٔ استاد، اینجا هم تازه می‌شود.<br>'
                'چهار فیلد بعدی فقط برای وقتی است که مدیر گروه عضو هیئت '
                'علمی نیست.'
            ),
        }),
        ('محتوا', {
            'fields': ('description', 'goals', 'research_areas', 'facilities')
        }),
        ('اطلاعات تماس', {
            'fields': ('phone', 'email', 'location', 'established_year')
        }),
        ('تحصیلات تکمیلی', {
            'fields': ('has_graduate', 'graduate_order'),
            'description': (
                'با زدن این تیک، گروه زیر منوی «معاونین ← معاونت آموزشی ← '
                'تحصیلات تکمیلی» می‌آید. ترتیب را با عدد تعیین کنید؛ '
                'کوچک‌تر بالاتر.'
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department')

    @admin.display(description='تعداد رشته')
    def majors_count(self, obj):
        n = obj.majors.filter(is_active=True).count()
        return format_html('<span style="color:#16a34a;font-weight:600;">{}</span>', n)
