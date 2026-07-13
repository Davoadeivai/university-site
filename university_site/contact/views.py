from django.shortcuts import render, get_object_or_404, redirect
from .models import ContactMessage, Alumni
from django.contrib import messages


def contact(request):
    if request.method == 'POST':
        data = request.POST
        msg = ContactMessage(
            full_name=data.get('full_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            subject=data.get('subject', 'general'),
            message=data.get('message', ''),
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        msg.save()
        messages.success(request, 'پیام شما با موفقیت ارسال شد.')
        return redirect('contact:contact')

    context = {'page_title': 'تماس با ما'}
    return render(request, 'contact/contact.html', context)


def alumni(request):
    alumni_list = Alumni.objects.all().order_by('-graduation_year')
    featured_alumni = Alumni.objects.filter(is_featured=True)[:6]
    context = {
        'alumni_list': alumni_list,
        'featured_alumni': featured_alumni,
        'page_title': 'فارغ‌التحصیلان',
    }
    return render(request, 'contact/alumni.html', context)


def industry(request):
    context = {'page_title': 'ارتباط با صنعت'}
    return render(request, 'contact/industry.html', context)
