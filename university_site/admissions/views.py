from django.shortcuts import render, redirect
from .models import AdmissionInfo, Application
from django.contrib import messages


def admissions_view(request):
    admission_infos = AdmissionInfo.objects.filter(is_active=True)
    context = {
        'admission_infos': admission_infos,
        'page_title': 'پذیرش دانشجو',
    }
    return render(request, 'admissions/admissions.html', context)


def apply(request):
    if request.method == 'POST':
        data = request.POST
        Application.objects.create(
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            national_id=data.get('national_id', ''),
            birth_date=data.get('birth_date', '2000-01-01'),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', ''),
            desired_major=data.get('desired_major', ''),
            degree=data.get('degree', 'bachelor'),
        )
        messages.success(request, 'درخواست شما با موفقیت ثبت شد. با شما تماس خواهیم گرفت.')
        return redirect('admissions:admissions')

    context = {'page_title': 'ثبت درخواست پذیرش'}
    return render(request, 'admissions/apply.html', context)
