import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dashboard', '0004_tuition_installments_enrollment_ta'),
    ]

    operations = [
        migrations.CreateModel(
            name='TuitionInstallmentPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(max_length=20, unique=True, verbose_name='سال تحصیلی')),
                ('ratio_initial', models.PositiveSmallIntegerField(default=40, verbose_name='درصد قسط ۱')),
                ('ratio_mid', models.PositiveSmallIntegerField(default=30, verbose_name='درصد قسط ۲')),
                ('ratio_exam', models.PositiveSmallIntegerField(default=30, verbose_name='درصد قسط ۳')),
                ('due_days_initial', models.PositiveSmallIntegerField(default=7, verbose_name='سررسید قسط ۱ (روز از شروع ترم)')),
                ('due_days_mid', models.PositiveSmallIntegerField(default=60, verbose_name='سررسید قسط ۲ (روز از شروع ترم)')),
                ('due_days_exam', models.PositiveSmallIntegerField(default=100, verbose_name='سررسید قسط ۳ (روز از شروع ترم)')),
                ('reminder_days_before', models.PositiveSmallIntegerField(default=3, verbose_name='یادآوری پیامک چند روز قبل')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('notes', models.TextField(blank=True, verbose_name='توضیحات')),
            ],
            options={
                'verbose_name': 'برنامه اقساط شهریه',
                'verbose_name_plural': 'برنامه‌های اقساط شهریه',
                'ordering': ['-academic_year'],
            },
        ),
        migrations.CreateModel(
            name='StudentDiscountClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_type', models.CharField(choices=[('sibling', 'تخفیف خواهر / برادر'), ('martyr', 'ایثارگری / خانواده شهید'), ('veteran', 'جانبازی / ایثارگری'), ('talent', 'استعداد درخشان'), ('other', 'سایر')], max_length=20, verbose_name='نوع تخفیف')),
                ('percent', models.PositiveSmallIntegerField(default=10, verbose_name='درصد تخفیف')),
                ('document', models.FileField(blank=True, null=True, upload_to='tuition_discounts/', verbose_name='مدرک پیوست')),
                ('notes', models.TextField(blank=True, verbose_name='توضیحات دانشجو')),
                ('status', models.CharField(choices=[('pending', 'در انتظار بررسی'), ('approved', 'تأیید شده'), ('rejected', 'رد شده')], default='pending', max_length=20, verbose_name='وضعیت')),
                ('admin_note', models.TextField(blank=True, verbose_name='یادداشت ادمین')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discount_claims', to='dashboard.semester', verbose_name='ترم')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discount_claims', to=settings.AUTH_USER_MODEL, verbose_name='دانشجو')),
            ],
            options={
                'verbose_name': 'تخفیف شهریه دانشجو',
                'verbose_name_plural': 'تخفیف‌های شهریه دانشجو',
                'ordering': ['-created_at'],
                'unique_together': {('student', 'semester', 'discount_type')},
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='due_date',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='سررسید قسط'),
        ),
        migrations.AddField(
            model_name='payment',
            name='exam_barcode',
            field=models.CharField(blank=True, db_index=True, max_length=64, verbose_name='بارکد کارت امتحان'),
        ),
        migrations.AddField(
            model_name='payment',
            name='method',
            field=models.CharField(blank=True, choices=[('online', 'پرداخت آنلاین (درگاه)'), ('card_to_card', 'کارت‌به‌کارت'), ('pos', 'کارت‌خوان / کارتخوان در مؤسسه'), ('bank_deposit', 'فیش بانکی / واریز به حساب'), ('cash', 'نقدی در امور مالی'), ('other', 'سایر')], default='online', max_length=20, verbose_name='روش پرداخت'),
        ),
        migrations.AddField(
            model_name='payment',
            name='method_notes',
            field=models.TextField(blank=True, verbose_name='توضیح روش پرداخت'),
        ),
        migrations.AddField(
            model_name='payment',
            name='receipt_file',
            field=models.FileField(blank=True, null=True, upload_to='tuition_receipts/', verbose_name='فیش / رسید آفلاین'),
        ),
        migrations.AddField(
            model_name='payment',
            name='receipt_ref',
            field=models.CharField(blank=True, max_length=100, verbose_name='شماره پیگیری / مرجع'),
        ),
        migrations.AddField(
            model_name='payment',
            name='reminder_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='آخرین یادآوری پیامکی'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('pending', 'در انتظار پرداخت'), ('review', 'در انتظار تأیید امور مالی'), ('paid', 'پرداخت شده'), ('failed', 'ناموفق'), ('refunded', 'بازگشت داده شده')], default='pending', max_length=20, verbose_name='وضعیت'),
        ),
    ]
