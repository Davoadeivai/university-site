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
    majors = list(
        department.majors.filter(is_active=True)
        .select_related('group').order_by('group__order', 'group__name',
                                          'degree', 'name')
    )

    # ── رشته‌ها زیر گروهِ خودشان ──
    # دانشکدهٔ مدیریت ۲۷ رشته دارد؛ ریختنشان در یک شبکه یعنی دیواری
    # از کارت که معلوم نیست کدام مال کدام گروه است. گروه‌بندی همان
    # ساختاری است که در دیتابیس هست و فقط روی صفحه دیده نمی‌شد.
    buckets = {}
    for major in majors:
        key = major.group_id
        if key not in buckets:
            buckets[key] = {'group': major.group, 'majors': []}
        buckets[key]['majors'].append(major)

    groups = list(department.groups.filter(is_active=True)
                  .order_by('order', 'name'))
    blocks = []
    for group in groups:
        bucket = buckets.pop(group.id, None)
        if bucket:
            blocks.append(bucket)
    # رشته‌ای که گروه ندارد نباید ناپدید شود
    orphans = buckets.pop(None, None)
    for leftover in buckets.values():
        blocks.append(leftover)
    if orphans:
        orphans['group'] = None
        blocks.append(orphans)

    # مقطع‌هایی که واقعاً در این دانشکده هستند — نه همهٔ گزینه‌های مدل
    seen = []
    for major in majors:
        label = major.get_degree_display()
        if (major.degree, label) not in seen:
            seen.append((major.degree, label))

    context = {
        'department': department,
        'majors': majors,
        'major_blocks': blocks,
        'degree_filters': seen,
        'professors': department.professors.filter(is_active=True),
        'labs': department.labs.filter(is_active=True),
        'page_title': department.name,
    }
    return render(request, 'academics/department_detail.html', context)


def majors_list(request):
    from core.degree_map import CANONICAL_DEGREES, major_degree_q, to_canonical_degree

    degree = request.GET.get('degree')
    majors = Major.objects.filter(is_active=True).select_related('department', 'group')
    if degree:
        majors = majors.filter(major_degree_q(degree))
    context = {
        'majors': majors,
        'degree': to_canonical_degree(degree) if degree else '',
        'degree_filters': CANONICAL_DEGREES,
        'page_title': 'رشته‌های تحصیلی',
    }
    return render(request, 'academics/majors.html', context)


def major_detail(request, slug):
    major = get_object_or_404(Major, slug=slug, is_active=True)
    courses = major.courses.all().order_by('semester')
    has_pdf = bool(major.curriculum_pdf)
    has_word = bool(major.curriculum_word)
    has_text = bool((major.curriculum or '').strip())

    view_format = (request.GET.get('view') or '').strip().lower()
    if view_format not in ('pdf', 'word', 'text'):
        if has_pdf:
            view_format = 'pdf'
        elif has_text:
            view_format = 'text'
        elif has_word:
            view_format = 'word'
        else:
            view_format = ''

    if view_format == 'pdf' and not has_pdf:
        view_format = 'text' if has_text else ('word' if has_word else '')
    if view_format == 'word' and not has_word:
        view_format = 'pdf' if has_pdf else ('text' if has_text else '')
    if view_format == 'text' and not has_text:
        view_format = 'pdf' if has_pdf else ('word' if has_word else '')

    context = {
        'major': major,
        'courses': courses,
        'has_pdf': has_pdf,
        'has_word': has_word,
        'has_text': has_text,
        'view_format': view_format,
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
    majors = group.majors.filter(is_active=True).order_by('degree', 'order', 'name')
    # گروه‌بندی رشته‌ها بر اساس مقطع (مثل عکس‌ها)
    majors_by_degree = {}
    for m in majors:
        label = m.get_degree_display()
        majors_by_degree.setdefault(label, []).append(m)
    professors = group.department.professors.filter(is_active=True) if hasattr(group.department, 'professors') else []
    context = {
        'group': group,
        'majors': majors,
        'majors_by_degree': majors_by_degree,
        'professors': professors,
        'page_title': group.name,
    }
    return render(request, 'academics/group_detail.html', context)
