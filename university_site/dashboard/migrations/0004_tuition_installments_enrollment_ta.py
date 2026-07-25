from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_major_fk_and_payment_gateway'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='teaching_assignment',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='enrollments',
                to='dashboard.teachingassignment',
                verbose_name='کلاس / استاد انتخابی',
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_no',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, verbose_name='شماره قسط'),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_stage',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', '—'),
                    ('initial', 'قسط اول (ثبت‌نام)'),
                    ('mid', 'قسط دوم (میانی)'),
                    ('exam_card', 'قسط سوم (کارت ورود به جلسه)'),
                ],
                default='',
                max_length=20,
                verbose_name='مرحله قسط',
            ),
        ),
        migrations.AlterModelOptions(
            name='payment',
            options={
                'ordering': ['installment_no', '-created_at'],
                'verbose_name': 'پرداخت سامانه آموزشی',
                'verbose_name_plural': 'پرداخت‌های سامانه آموزشی',
            },
        ),
    ]
