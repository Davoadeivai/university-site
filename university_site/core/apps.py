from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'سایت و محتوای عمومی'

    def ready(self):
        # کش context سراسری با هر تغییر محتوا باطل شود تا ویرایش ادمین
        # بلافاصله روی سایت دیده شود (نه با تأخیر ۶۰ ثانیه‌ای کش)
        from core.cache_invalidation import register
        register()
