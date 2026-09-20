"""قفلِ پس از چند تلاش ناموفق برای ورود.

چرا کپچا کافی نبود
──────────────────
کپچا جلوی ربات ساده را می‌گیرد، ولی سه چیز را نمی‌گیرد: سرویس‌های
حل‌کپچا که ارزان‌اند، حمله‌ای که رمزِ پرتکرار را روی هزار نام کاربری
امتحان می‌کند، و مهم‌تر از همه ورودِ \u200E/admin/login/\u200E که اصلاً کپچا
ندارد. با کد ملی به‌عنوان نام کاربری، فهرست نام‌ها هم عملاً حدس‌زدنی
است.

چه می‌کند
─────────
شکستِ ورود را دو جا می‌شمارد: روی نشانی اینترنتی درخواست‌کننده، و
روی شناسه‌ای که وارد کرده. اولی حملهٔ یک منبع را می‌بندد، دومی
حمله‌ای را که از صدها نشانی روی یک حساب می‌آید.

پس از رسیدن به سقف، پاسخ ۴۲۹ است تا پایان مهلت — بی‌آنکه رمز اصلاً
بررسی شود.

چرا میان‌افزار
──────────────
تا هر دری که به ورود باز می‌شود زیر همین قاعده باشد: صفحهٔ ورود
سایت، ورود پنل مدیریت، و هر صفحهٔ ورودی که بعداً اضافه شود.
"""
from __future__ import annotations

from django.core.cache import cache
from django.http import HttpResponse
from django.utils.translation import gettext as _

# مسیرهایی که رمز در آن‌ها بررسی می‌شود.
LOGIN_PATHS = ('/accounts/login/', '/admin/login/', '/admin/')

# نام فیلدهایی که ممکن است شناسهٔ کاربر در آن‌ها بیاید.
IDENTITY_FIELDS = ('national_id', 'username', 'login_id', 'email')

MAX_FAILURES = 8
WINDOW_SECONDS = 15 * 60
LOCK_SECONDS = 15 * 60


def _client_ip(request) -> str:
    """نشانی واقعی، نه نشانی پراکسی.

    سایت پشت LiteSpeed است، پس \u200EREMOTE_ADDR\u200E خودِ سرور می‌شود و همهٔ
    کاربران یک نشانی می‌گیرند — یعنی قفلی که همه را با هم می‌بندد.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:60]
    return (request.META.get('REMOTE_ADDR') or '?')[:60]


def _identity(request) -> str:
    for field in IDENTITY_FIELDS:
        value = (request.POST.get(field) or '').strip()
        if value:
            return value[:60]
    return ''


def _keys(request):
    keys = ['loginguard:ip:%s' % _client_ip(request)]
    identity = _identity(request)
    if identity:
        keys.append('loginguard:id:%s' % identity)
    return keys


def is_locked(request) -> bool:
    return any(cache.get(key, 0) >= MAX_FAILURES for key in _keys(request))


def note_failure(request) -> None:
    for key in _keys(request):
        # \u200Eadd\u200E سپس \u200Eincr\u200E: پنجره از نخستین شکست شروع می‌شود و با هر
        # شکست تازه جلو نمی‌رود، وگرنه قفل عملاً ابدی می‌شد.
        if cache.add(key, 1, timeout=WINDOW_SECONDS):
            continue
        try:
            cache.incr(key)
        except ValueError:                     # کلید میان دو خط منقضی شد
            cache.set(key, 1, timeout=WINDOW_SECONDS)


def clear(request) -> None:
    """ورود موفق، صفحهٔ سفید."""
    cache.delete_many(_keys(request))


def _too_many(request) -> HttpResponse:
    minutes = max(1, LOCK_SECONDS // 60)
    body = _('تلاش‌های ناموفق زیاد بوده است. لطفاً %(minutes)d دقیقهٔ '
             'دیگر دوباره امتحان کنید.') % {'minutes': minutes}
    response = HttpResponse(body, status=429, content_type='text/plain; charset=utf-8')
    response['Retry-After'] = str(LOCK_SECONDS)
    return response


class LoginRateLimitMiddleware:
    """شمارش شکست‌ها و بستنِ در، پیش و پس از هر تلاش ورود."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        watched = (request.method == 'POST'
                   and any(request.path.startswith(p) for p in LOGIN_PATHS))
        if not watched:
            return self.get_response(request)

        if is_locked(request):
            return _too_many(request)

        was_anonymous = not request.user.is_authenticated
        response = self.get_response(request)

        # ورودِ موفق همیشه به جای دیگری می‌فرستد؛ ماندن روی همان صفحه
        # یعنی رمز پذیرفته نشده.
        succeeded = (response.status_code in (301, 302)
                     and request.user.is_authenticated)
        if succeeded:
            clear(request)
        elif was_anonymous and response.status_code == 200:
            note_failure(request)
            if is_locked(request):
                return _too_many(request)
        return response
