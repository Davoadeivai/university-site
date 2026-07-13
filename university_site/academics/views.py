from django.shortcuts import render, get_object_or_404
from .models import Department, Major, AcademicCalendar, Laboratory, AcademicGroup


def departments_list(request):
    departments = Department.objects.filter(is_active=True)
    context = {
        'departments': departments,
        'page_title': 'دانشکده‌ها و گروه‌های آموزشی',
    }
    return render(request, 'academics/departments.html', context)


def department_detail(request, slug):
    department = get_object_or_404(Department, slug=slug, is_active=True)
    majors = department.majors.filter(is_active=True)
    professors = department.professors.filter(is_active=True)
    labs = department.labs.filter(is_active=True)
    context = {
        'department': department,
        'majors': majors,
        'professors': professors,
        'labs': labs,
        'page_title': department.name,
    }
    return render(request, 'academics/department_detail.html', context)


def majors_list(request):
    degree = request.GET.get('degree')
    majors = Major.objects.filter(is_active=True)
    if degree:
        majors = majors.filter(degree=degree)
    context = {
        'majors': majors,
        'degree': degree,
        'page_title': 'رشته‌های تحصیلی',
    }
    return render(request, 'academics/majors.html', context)


def major_detail(request, slug):
    major = get_object_or_404(Major, slug=slug, is_active=True)
    courses = major.courses.all().order_by('semester')
    context = {
        'major': major,
        'courses': courses,
        'page_title': f"{major.name} - {major.get_degree_display()}",
    }
    return render(request, 'academics/major_detail.html', context)


def academic_calendar(request):
    calendar_items = AcademicCalendar.objects.all().order_by('start_date')
    context = {
        'calendar_items': calendar_items,
        'page_title': 'تقویم آموزشی',
    }
    return render(request, 'academics/calendar.html', context)


def students_panel(request):
    context = {'page_title': 'پنل دانشجویی'}
    return render(request, 'academics/students_panel.html', context)


def professors_panel(request):
    context = {'page_title': 'پنل اساتید'}
    return render(request, 'academics/professors_panel.html', context)


def elearning(request):
    context = {'page_title': 'آموزش الکترونیکی'}
    return render(request, 'academics/elearning.html', context)


def groups_list(request):
    """لیست تمام گروه‌های آموزشی"""
    dept_id = request.GET.get('dept')
    groups = AcademicGroup.objects.filter(is_active=True).select_related('department')
    departments = Department.objects.filter(is_active=True)
    if dept_id:
        groups = groups.filter(department__id=dept_id)
    context = {
        'groups': groups,
        'departments': departments,
        'selected_dept': dept_id,
        'page_title': 'گروه‌های آموزشی',
    }
    return render(request, 'academics/groups_list.html', context)


def group_detail(request, slug):
    """صفحه جزئیات یک گروه آموزشی"""
    group = get_object_or_404(AcademicGroup, slug=slug, is_active=True)
    majors = group.department.majors.filter(is_active=True)
    professors = group.department.professors.filter(is_active=True)
    context = {
        'group': group,
        'majors': majors,
        'professors': professors,
        'page_title': group.name,
    }
    return render(request, 'academics/group_detail.html', context)
