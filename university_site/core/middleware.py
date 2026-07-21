"""اجبار زبان فارسی برای کل پروژه (ادمین و سایت)."""
from django.utils import translation


class ForcePersianMiddleware:
    """
    LocaleMiddleware ممکن است به‌خاطر Accept-Language مرورگر، ادمین را انگلیسی کند.
    این میان‌افزار بعد از آن اجرا می‌شود و زبان را روی فارسی نگه می‌دارد.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        translation.activate('fa')
        request.LANGUAGE_CODE = 'fa'
        response = self.get_response(request)
        response['Content-Language'] = 'fa'
        return response
