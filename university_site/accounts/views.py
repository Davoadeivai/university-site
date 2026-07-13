from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings as django_settings
from .models import UserProfile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'خوش آمدید، {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next', '/dashboard/')
            return redirect(next_url)
        else:
            messages.error(request, 'نام کاربری یا رمز عبور اشتباه است.')

    context = {'page_title': 'ورود به سامانه'}
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    logout(request)
    messages.info(request, 'با موفقیت خارج شدید.')
    return redirect('/')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if not username or not password1 or not password2:
            messages.error(request, 'لطفاً تمام فیلدهای الزامی را پر کنید.')
        elif password1 != password2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        elif len(password1) < 8:
            messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'این نام کاربری قبلاً استفاده شده است.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
            )
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f'حساب کاربری با موفقیت ساخته شد. خوش آمدید، {user.username}!')
            return redirect('dashboard:dashboard')

    context = {'page_title': 'ثبت‌نام'}
    return render(request, 'accounts/register.html', context)


@login_required
def profile(request):
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
    context = {
        'profile': profile_obj,
        'page_title': 'پروفایل من',
    }
    return render(request, 'accounts/profile.html', context)


# ─────────────────────────────────────────────────────────────────
# مرحله ۱: دریافت ایمیل و ارسال لینک بازیابی
# ─────────────────────────────────────────────────────────────────
def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'لطفاً آدرس ایمیل را وارد کنید.')
        else:
            users = User.objects.filter(email__iexact=email, is_active=True)
            if users.exists():
                user = users.first()
                uid   = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                reset_url = request.build_absolute_uri(
                    f'/accounts/password-reset/{uid}/{token}/'
                )

                subject = 'بازیابی رمز عبور — دانشگاه جامع'
                html_body = render_to_string(
                    'accounts/email/password_reset_email.html',
                    {'user': user, 'reset_url': reset_url},
                )
                plain_body = (
                    f'سلام {user.get_full_name() or user.username}،\n\n'
                    f'برای بازیابی رمز عبور روی لینک زیر کلیک کنید:\n{reset_url}\n\n'
                    f'این لینک ۱ ساعت اعتبار دارد.\n\n'
                    f'اگر این درخواست از شما نیست، این ایمیل را نادیده بگیرید.'
                )
                try:
                    send_mail(
                        subject,
                        plain_body,
                        django_settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_body,
                        fail_silently=False,
                    )
                except Exception:
                    pass   # حتی در صورت خطای SMTP پیام موفقیت نشان می‌دهیم

            # برای جلوگیری از user-enumeration همیشه پیام موفقیت نشان دهید
            messages.success(
                request,
                'اگر این ایمیل در سامانه ثبت شده باشد، لینک بازیابی ارسال شد.'
            )
            return redirect('accounts:password_reset_request')

    return render(request, 'accounts/password_reset_request.html',
                  {'page_title': 'بازیابی رمز عبور'})


# ─────────────────────────────────────────────────────────────────
# مرحله ۲: تأیید توکن و نمایش فرم رمز جدید
# ─────────────────────────────────────────────────────────────────
def password_reset_confirm(request, uidb64, token):
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    valid = user is not None and default_token_generator.check_token(user, token)

    if not valid:
        messages.error(request, 'لینک بازیابی نامعتبر یا منقضی شده است.')
        return redirect('accounts:password_reset_request')

    if request.method == 'POST':
        p1 = request.POST.get('password1', '')
        p2 = request.POST.get('password2', '')
        if not p1 or not p2:
            messages.error(request, 'لطفاً هر دو فیلد رمز عبور را پر کنید.')
        elif p1 != p2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        elif len(p1) < 8:
            messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
        else:
            user.set_password(p1)
            user.save()
            messages.success(request, 'رمز عبور با موفقیت تغییر کرد. اکنون وارد شوید.')
            return redirect('accounts:login')

    return render(request, 'accounts/password_reset_confirm.html', {
        'uidb64': uidb64,
        'token':  token,
        'page_title': 'تنظیم رمز عبور جدید',
    })
