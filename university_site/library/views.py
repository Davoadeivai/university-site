from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Article, Book, LibraryMembership


def library_home(request):
    query = request.GET.get('q', '').strip()
    subject = request.GET.get('subject', '').strip()
    language = request.GET.get('language', '').strip()
    availability = request.GET.get('availability', '').strip()
    year = request.GET.get('year', '').strip()

    books = Book.objects.all()
    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(isbn__icontains=query)
            | Q(publisher__icontains=query)
            | Q(subject__icontains=query)
        )
    if subject:
        books = books.filter(subject=subject)
    if language:
        books = books.filter(language=language)
    if year.isdigit():
        books = books.filter(year=int(year))
    if availability == 'available':
        books = books.filter(is_available=True, copies_available__gt=0)
    elif availability == 'unavailable':
        books = books.filter(Q(is_available=False) | Q(copies_available=0))

    paginator = Paginator(books.order_by('title'), 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    subjects = list(
        Book.objects.exclude(subject='')
        .values_list('subject', flat=True)
        .distinct()
        .order_by('subject')
    )
    languages = list(
        Book.objects.exclude(language='')
        .values_list('language', flat=True)
        .distinct()
        .order_by('language')
    )
    years = list(Book.objects.values_list('year', flat=True).distinct().order_by('-year'))

    recent_articles = Article.objects.all()[:4]
    stats = {
        'books': Book.objects.count(),
        'available': Book.objects.filter(is_available=True, copies_available__gt=0).count(),
        'articles': Article.objects.count(),
        'subjects': len(subjects),
    }

    context = {
        'page_obj': page_obj,
        'books': page_obj.object_list,
        'query': query,
        'subject': subject,
        'language': language,
        'availability': availability,
        'year': year,
        'subjects': subjects,
        'languages': languages,
        'years': years,
        'recent_articles': recent_articles,
        'recent_books': Book.objects.filter(is_available=True).order_by('-id')[:6],
        'stats': stats,
        'page_title': 'مرکز اطلاع رسانی و کتابخانه مرکزی',
        'result_count': paginator.count,
    }
    return render(request, 'library/library.html', context)


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    related = Book.objects.filter(subject=book.subject).exclude(pk=book.pk)[:4] if book.subject else Book.objects.exclude(pk=book.pk)[:4]
    context = {
        'book': book,
        'related': related,
        'page_title': book.title,
    }
    return render(request, 'library/book_detail.html', context)


def articles_list(request, section=''):
    query = request.GET.get('q', '').strip()
    year = request.GET.get('year', '').strip()
    section = section or request.GET.get('section', '').strip()
    articles = Article.objects.all()
    if section in dict(Article.SECTION_CHOICES):
        articles = articles.filter(section=section)
    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(authors__icontains=query)
            | Q(keywords__icontains=query)
            | Q(journal__icontains=query)
        )
    if year.isdigit():
        articles = articles.filter(year=int(year))

    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    years = Article.objects.values_list('year', flat=True).distinct().order_by('-year')

    titles = {
        'faculty': 'مقالات اعضای هیات علمی',
        'conference': 'بانک مقالات همایش ها',
    }
    empty_hint = (
        'هیچ مقاله‌ای در این دسته موجود نیست؛ اگر نام زیر‌دسته‌ها نمایش داده می‌شود، '
        'آن‌ها دارای مقالاتی هستند.'
        if section in ('faculty', 'conference') else ''
    )

    context = {
        'page_obj': page_obj,
        'articles': page_obj.object_list,
        'query': query,
        'year': year,
        'years': years,
        'section': section,
        'empty_hint': empty_hint,
        'page_title': titles.get(section, 'مقالات علمی'),
        'result_count': paginator.count,
    }
    return render(request, 'library/articles.html', context)


def faculty_articles(request):
    return articles_list(request, section='faculty')


def conference_articles(request):
    return articles_list(request, section='conference')


def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    keywords = [k.strip() for k in article.keywords.split(',') if k.strip()] if article.keywords else []
    context = {
        'article': article,
        'keywords': keywords,
        'page_title': article.title,
    }
    return render(request, 'library/article_detail.html', context)


def membership(request):
    membership_result = None
    check_id = request.GET.get('check_id', '').strip()

    if request.method == 'POST':
        from core.sms import check_rate_limit
        allowed, rl_msg = check_rate_limit(request, scope='library_membership', limit=10, window=300)
        action = request.POST.get('action', 'register')
        if not allowed:
            messages.error(request, rl_msg)
        elif action == 'check':
            sid = request.POST.get('student_id', '').strip()
            membership_result = LibraryMembership.objects.filter(student_id=sid).first()
            if not membership_result:
                messages.warning(request, 'عضویت‌ی با این شماره دانشجویی یافت نشد.')
            check_id = sid
        else:
            full_name = request.POST.get('full_name', '').strip()
            student_id = request.POST.get('student_id', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            if not full_name or not student_id or not phone:
                messages.error(request, 'لطفاً نام، شماره دانشجویی و شماره تماس را کامل وارد کنید.')
            elif not student_id.isdigit():
                messages.error(request, 'شماره دانشجویی باید عددی باشد.')
            elif LibraryMembership.objects.filter(student_id=student_id).exists():
                messages.error(request, 'شماره دانشجویی قبلاً ثبت شده است. از بخش «پیگیری وضعیت» استفاده کنید.')
            else:
                LibraryMembership.objects.create(
                    full_name=full_name,
                    student_id=student_id,
                    email=email,
                    phone=phone,
                )
                messages.success(request, 'درخواست عضویت ثبت شد و در انتظار تایید است.')
                return redirect('library:membership')

    elif check_id:
        membership_result = LibraryMembership.objects.filter(student_id=check_id).first()

    context = {
        'page_title': 'عضویت در کتابخانه',
        'membership_result': membership_result,
        'check_id': check_id,
    }
    return render(request, 'library/membership.html', context)
