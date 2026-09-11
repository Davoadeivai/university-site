from django.shortcuts import render, get_object_or_404, redirect
from .models import ContactMessage, Alumni
from django.contrib import messages

from core.iran import normalize_digits, validate_image_upload

# سقف فیش، بالاتر از سقف دو مگابایتیِ فرم‌های پذیرش.
#
# دانشجو فیش را با دوربین گوشی می‌گیرد و عکس خام گوشی‌های امروزی
# به‌راحتی سه چهار مگابایت است. با سقف دو مگابایت، فرم درست همان
# لحظه‌ای رد می‌کرد که دانشجو کاری از دستش برنمی‌آمد. پس از ذخیره،
# ShrinkImagesMixin عکس را به ۱۶۰۰ پیکسل کوچک می‌کند.
RECEIPT_MAX_BYTES = 5 * 1024 * 1024


def contact(request):
    if request.method == 'POST':
        data = request.POST
        subject = data.get('subject', 'general')
        if subject not in dict(ContactMessage.SUBJECT_CHOICES):
            subject = 'general'

        is_receipt = subject == ContactMessage.RECEIPT_SUBJECT
        upload = request.FILES.get('attachment')
        student_number = normalize_digits(data.get('student_number', ''))

        # فیش بدون شمارهٔ دانشجویی، عکسِ واریزی است که معلوم نیست به
        # حساب چه کسی بنشیند — امور مالی کاری با آن نمی‌تواند بکند.
        error = validate_image_upload(
            upload, 'تصویر فیش واریزی', required=is_receipt,
            max_bytes=RECEIPT_MAX_BYTES)
        if not error and is_receipt and not student_number:
            error = 'برای ارسال فیش، شمارهٔ دانشجویی الزامی است.'

        if error:
            messages.error(request, error)
            # آنچه نوشته بود نباید پاک شود؛ فقط فایل دوباره لازم است.
            return render(request, 'contact/contact.html', {
                'page_title': _page_title(subject),
                'selected_subject': subject,
                'subject_choices': ContactMessage.SUBJECT_CHOICES,
                'receipt_subject': ContactMessage.RECEIPT_SUBJECT,
                'submitted': data,
            })

        msg = ContactMessage(
            full_name=data.get('full_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            subject=subject,
            message=data.get('message', ''),
            student_number=student_number,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        if upload:
            msg.attachment = upload
        msg.save()
        messages.success(
            request,
            'فیش شما دریافت شد و برای بررسی به امور مالی ارجاع می‌شود.'
            if is_receipt else 'پیام شما با موفقیت ارسال شد.')
        return redirect('contact:contact')

    selected_subject = request.GET.get('to', 'general')
    if selected_subject not in dict(ContactMessage.SUBJECT_CHOICES):
        selected_subject = 'general'
    context = {
        'page_title': _page_title(selected_subject),
        'selected_subject': selected_subject,
        'subject_choices': ContactMessage.SUBJECT_CHOICES,
        'receipt_subject': ContactMessage.RECEIPT_SUBJECT,
    }
    return render(request, 'contact/contact.html', context)


def _page_title(subject: str) -> str:
    return {
        'presidency': 'ارتباط با ریاست',
        ContactMessage.RECEIPT_SUBJECT: 'ارسال فیش واریزی شهریه',
    }.get(subject, 'تماس با ما')


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
    from research.models import IndustryPartnership
    partners = IndustryPartnership.objects.filter(is_active=True).order_by('company_name')
    context = {
        'page_title': 'ارتباط با صنعت',
        'partners': partners,
    }
    return render(request, 'contact/industry.html', context)
