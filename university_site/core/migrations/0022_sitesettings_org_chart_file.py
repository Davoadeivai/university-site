# Generated manually for org chart file on about page settings

import core.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_document_safe_upload_paths'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='org_chart_file',
            field=models.FileField(
                blank=True,
                help_text='PDF، تصویر (JPG/PNG/…) یا Word. برای حذف، تیک «پاک کردن» را بزنید و ذخیره کنید.',
                null=True,
                upload_to=core.models._org_chart_file_upload_to,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'doc', 'docx'],
                    ),
                ],
                verbose_name='فایل چارت سازمانی',
            ),
        ),
    ]
