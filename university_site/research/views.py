from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import (
    Conference,
    IndustryPartnership,
    Journal,
    ResearchProject,
    Thesis,
)


def research_home(request):
    projects = ResearchProject.objects.filter(is_featured=True)[:6]
    if not projects:
        projects = ResearchProject.objects.all()[:6]
    journals = Journal.objects.filter(is_active=True)[:6]
    upcoming_conferences = Conference.objects.filter(is_upcoming=True).order_by('date')[:4]
    partners = IndustryPartnership.objects.filter(is_active=True)[:8]
    recent_theses = Thesis.objects.all()[:4]
    context = {
        'projects': projects,
        'journals': journals,
        'upcoming_conferences': upcoming_conferences,
        'partners': partners,
        'recent_theses': recent_theses,
        'stats': {
            'projects': ResearchProject.objects.count(),
            'theses': Thesis.objects.count(),
            'conferences': Conference.objects.count(),
            'journals': Journal.objects.filter(is_active=True).count(),
        },
        'page_title': 'معاونت پژوهشی',
    }
    return render(request, 'research/research.html', context)


def projects_list(request):
    status = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    projects = ResearchProject.objects.all()
    if status:
        projects = projects.filter(status=status)
    if query:
        projects = projects.filter(
            Q(title__icontains=query) | Q(researcher__icontains=query) | Q(description__icontains=query)
        )
    paginator = Paginator(projects, 9)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'projects': page_obj.object_list,
        'status': status,
        'query': query,
        'page_title': 'پروژه‌های پژوهشی',
        'result_count': paginator.count,
    }
    return render(request, 'research/projects.html', context)


def project_detail(request, pk):
    project = get_object_or_404(ResearchProject, pk=pk)
    related = ResearchProject.objects.filter(status=project.status).exclude(pk=pk)[:3]
    context = {
        'project': project,
        'related': related,
        'page_title': project.title,
    }
    return render(request, 'research/project_detail.html', context)


def theses_list(request):
    query = request.GET.get('q', '').strip()
    degree = request.GET.get('degree', '').strip()
    year = request.GET.get('year', '').strip()
    department = request.GET.get('department', '').strip()

    theses = Thesis.objects.all()
    if query:
        theses = theses.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(supervisor__icontains=query)
            | Q(keywords__icontains=query)
        )
    if degree:
        theses = theses.filter(degree=degree)
    if year.isdigit():
        theses = theses.filter(year=int(year))
    if department:
        theses = theses.filter(department=department)

    paginator = Paginator(theses, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    years = Thesis.objects.values_list('year', flat=True).distinct().order_by('-year')
    departments = (
        Thesis.objects.exclude(department='')
        .values_list('department', flat=True)
        .distinct()
        .order_by('department')
    )

    context = {
        'page_obj': page_obj,
        'theses': page_obj.object_list,
        'query': query,
        'degree': degree,
        'year': year,
        'department': department,
        'years': years,
        'departments': departments,
        'page_title': 'پایان‌نامه‌ها',
        'result_count': paginator.count,
    }
    return render(request, 'research/theses.html', context)


def thesis_detail(request, pk):
    thesis = get_object_or_404(Thesis, pk=pk)
    keywords = [k.strip() for k in thesis.keywords.split(',') if k.strip()] if thesis.keywords else []
    related = Thesis.objects.filter(degree=thesis.degree).exclude(pk=pk)[:3]
    context = {
        'thesis': thesis,
        'keywords': keywords,
        'related': related,
        'page_title': thesis.title,
    }
    return render(request, 'research/thesis_detail.html', context)


def conferences_list(request):
    scope = request.GET.get('scope', 'all').strip()
    query = request.GET.get('q', '').strip()
    conferences = Conference.objects.all()
    if scope == 'upcoming':
        conferences = conferences.filter(is_upcoming=True).order_by('date')
    elif scope == 'past':
        conferences = conferences.filter(is_upcoming=False).order_by('-date')
    else:
        conferences = conferences.order_by('-date')
    if query:
        conferences = conferences.filter(
            Q(title__icontains=query) | Q(location__icontains=query) | Q(organizer__icontains=query)
        )
    paginator = Paginator(conferences, 9)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'conferences': page_obj.object_list,
        'scope': scope,
        'query': query,
        'page_title': 'همایش‌ها و کنفرانس‌ها',
        'result_count': paginator.count,
    }
    return render(request, 'research/conferences.html', context)


def conference_detail(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    context = {
        'conference': conference,
        'page_title': conference.title,
    }
    return render(request, 'research/conference_detail.html', context)


def journals_list(request):
    """نشریات علمی — مطابق سایت رسمی با دو دسته اصلی"""
    category = request.GET.get('category', '').strip()
    journals = Journal.objects.filter(is_active=True)
    if category in dict(Journal.CATEGORY_CHOICES):
        journals = journals.filter(category=category)

    scientific = Journal.objects.filter(is_active=True, category='scientific')
    online_sub = Journal.objects.filter(is_active=True, category='online_sub')

    context = {
        'journals': journals,
        'scientific': scientific,
        'online_sub': online_sub,
        'current_category': category,
        'page_title': 'نشریات علمی',
        'show_hub': not category,
    }
    return render(request, 'research/journals.html', context)


def journal_detail(request, slug):
    journal = get_object_or_404(Journal, slug=slug, is_active=True)
    context = {
        'journal': journal,
        'page_title': journal.title,
    }
    return render(request, 'research/journal_detail.html', context)
