from django.apps import AppConfig


class AdmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admissions'
    verbose_name = 'پذیرش و ثبت‌نام'

    def ready(self):
        from . import signals  # noqa: F401
