from django.shortcuts import render, get_object_or_404
from .models import Professor, Publication


def professors_list(request):
    department = request.GET.get('department')
    rank = request.GET.get('rank')
    professors = Professor.objects.filter(is_active=True)
    if department:
        professors = professors.filter(department__slug=department)
    if rank:
        professors = professors.filter(rank=rank)
    context = {
        'professors': professors,
        'department': department,
        'rank': rank,
        'page_title': 'هیئت علمی',
    }
    return render(request, 'faculty/professors_list.html', context)


def professor_detail(request, slug):
    professor = get_object_or_404(Professor, slug=slug, is_active=True)
    publications = professor.publications.all().order_by('-year')
    context = {
        'professor': professor,
        'publications': publications,
        'page_title': professor.get_full_name(),
    }
    return render(request, 'faculty/professor_detail.html', context)
