from django.contrib import admin
from django.utils.html import format_html
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
    list_display    = ['name', 'group', 'department', 'degree', 'order', 'capacity', 'is_active']
    list_filter     = ['degree', 'group', 'department', 'is_active']
    list_editable   = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines         = [CourseInline]
    search_fields   = ['name', 'description']
    autocomplete_fields = ['group', 'department']
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'slug', 'department', 'group', 'degree', 'order', 'is_active')
        }),
        ('محتوا', {
            'fields': ('description', 'objectives', 'job_market', 'curriculum', 'admission_requirements')
        }),
        ('ظرفیت و شهریه', {
            'fields': ('total_credits', 'capacity', 'tuition_fee')
        }),
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'major', 'credits', 'course_type', 'semester']
    list_filter = ['course_type', 'semester', 'major__degree', 'major']
    search_fields = ['name', 'code', 'major__name']
    autocomplete_fields = ['major']
    fieldsets = (
        ('اطلاعات درس', {
            'fields': ('major', 'name', 'code', 'credits', 'course_type', 'semester', 'prerequisites')
        }),
        ('توضیحات', {
            'fields': ('description',),
        }),
    )


@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display  = ['title', 'semester', 'academic_year', 'start_date', 'end_date', 'is_important']
    list_filter   = ['semester', 'academic_year', 'is_important']
    list_editable = ['is_important']


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'supervisor', 'location', 'is_active']
    list_filter  = ['department', 'is_active']
    search_fields = ['name', 'supervisor']


@admin.register(AcademicGroup)
class AcademicGroupAdmin(admin.ModelAdmin):
    list_display        = ['name', 'department', 'head', 'majors_count', 'order', 'is_active']
    list_editable       = ['order', 'is_active']
    list_filter         = ['department', 'is_active']
    search_fields       = ['name', 'head', 'description', 'research_areas']
    prepopulated_fields = {'slug': ('name',)}
    inlines             = [GroupMajorInline]
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('department', 'name', 'slug', 'order', 'is_active', 'image'),
            'description': 'برای ویرایش رشته‌های هر مقطع، از جدول پایین صفحه («رشته‌ها و مقاطع این گروه») استفاده کنید.',
        }),
        ('مدیر گروه', {
            'fields': ('head', 'head_photo', 'head_email', 'head_phone')
        }),
        ('محتوا', {
            'fields': ('description', 'goals', 'research_areas', 'facilities')
        }),
        ('اطلاعات تماس', {
            'fields': ('phone', 'email', 'location', 'established_year')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department')

    @admin.display(description='تعداد رشته')
    def majors_count(self, obj):
        n = obj.majors.filter(is_active=True).count()
        return format_html('<span style="color:#16a34a;font-weight:600;">{}</span>', n)
