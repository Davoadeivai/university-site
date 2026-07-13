from django.shortcuts import render
from .models import ResearchProject, Journal, Thesis, Conference, IndustryPartnership


def research_home(request):
    projects = ResearchProject.objects.filter(is_featured=True)[:6]
    journals = Journal.objects.filter(is_active=True)[:4]
    upcoming_conferences = Conference.objects.filter(is_upcoming=True).order_by('date')[:4]
    context = {
        'projects': projects,
        'journals': journals,
        'upcoming_conferences': upcoming_conferences,
        'page_title': 'پژوهش',
    }
    return render(request, 'research/research.html', context)


def theses_list(request):
    query = request.GET.get('q', '')
    theses = Thesis.objects.all()
    if query:
        theses = theses.filter(title__icontains=query) | theses.filter(author__icontains=query)
    context = {
        'theses': theses,
        'query': query,
        'page_title': 'پایان‌نامه‌ها',
    }
    return render(request, 'research/theses.html', context)


def conferences_list(request):
    conferences = Conference.objects.all().order_by('-date')
    context = {
        'conferences': conferences,
        'page_title': 'همایش‌ها و کنفرانس‌ها',
    }
    return render(request, 'research/conferences.html', context)
