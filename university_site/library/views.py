from django.shortcuts import render
from .models import Book, Article, LibraryMembership
from django.contrib import messages
from django.shortcuts import redirect


def library_home(request):
    query = request.GET.get('q', '')
    books = Book.objects.filter(is_available=True)
    if query:
        books = books.filter(title__icontains=query) | books.filter(author__icontains=query)
    recent_books = Book.objects.filter(is_available=True)[:8]
    context = {
        'books': books,
        'query': query,
        'recent_books': recent_books,
        'page_title': 'کتابخانه',
    }
    return render(request, 'library/library.html', context)


def membership(request):
    if request.method == 'POST':
        data = request.POST
        if not LibraryMembership.objects.filter(student_id=data.get('student_id')).exists():
            LibraryMembership.objects.create(
                full_name=data.get('full_name', ''),
                student_id=data.get('student_id', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
            )
            messages.success(request, 'درخواست عضویت شما ثبت شد.')
        else:
            messages.error(request, 'شماره دانشجویی قبلاً ثبت شده است.')
        return redirect('library:library')

    context = {'page_title': 'عضویت در کتابخانه'}
    return render(request, 'library/membership.html', context)
