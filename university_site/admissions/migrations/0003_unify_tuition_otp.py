# TuitionStructure → Major FK; drop Tuition/TuitionHistory; OTP attempts

import django.db.models.deletion
from django.db import migrations, models


def link_structures(apps, schema_editor):
    TuitionStructure = apps.get_model('admissions', 'TuitionStructure')
    Tuition = apps.get_model('admissions', 'Tuition')
    TuitionHistory = apps.get_model('admissions', 'TuitionHistory')
    Major = apps.get_model('academics', 'Major')

    fallback = Major.objects.order_by('id').first()
    seen = set()

    for ts in list(TuitionStructure.objects.all()):
        major_text = ts.major if isinstance(ts.major, str) else ''
        found = None
        name = (major_text or '').strip()
        if name:
            found = Major.objects.filter(name__iexact=name).first()
            if not found:
                found = Major.objects.filter(name__icontains=name).first()
        if not found:
            found = fallback
        if not found:
            ts.delete()
            continue
        key = (found.id, ts.academic_year)
        if key in seen:
            ts.delete()
            continue
        seen.add(key)
        ts.major_ref_id = found.id
        ts.save(update_fields=['major_ref'])

    for t in Tuition.objects.all():
        found = Major.objects.filter(name__iexact=(t.major or '').strip()).first() if t.major else None
        if not found:
            found = Major.objects.filter(name__icontains=(t.major or '')[:30]).first() or fallback
        if not found:
            continue
        key = (found.id, t.academic_year)
        if key in seen:
            continue
        seen.add(key)
        TuitionStructure.objects.create(
            major_ref_id=found.id,
            academic_year=t.academic_year,
            fixed_fee=t.base_fee,
            theory_fee=t.per_credit_fee,
            practical_fee=t.per_credit_fee,
            notes=t.notes or '',
            is_active=True,
        )

    for h in TuitionHistory.objects.all():
        found = Major.objects.filter(name__iexact=(h.major or '').strip()).first()
        if not found:
            found = Major.objects.filter(name__icontains=(h.major or '')[:30]).first() or fallback
        if not found:
            continue
        key = (found.id, h.academic_year)
        if key in seen:
            continue
        seen.add(key)
        TuitionStructure.objects.create(
            major_ref_id=found.id,
            academic_year=h.academic_year,
            fixed_fee=h.fixed_fee,
            theory_fee=h.theory_fee,
            practical_fee=h.practical_fee,
            notes=h.notes or '',
            is_active=False,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0002_full_application_tuition'),
        ('academics', '0003_major_group_and_degree_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='admissionotp',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='تلاش ناموفق'),
        ),
        migrations.AddField(
            model_name='tuitionstructure',
            name='major_ref',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tuition_structures',
                to='academics.major',
                verbose_name='رشته',
            ),
        ),
        migrations.RunPython(link_structures, noop),
        # حذف unique قدیمی و فیلدهای متنی
        migrations.AlterUniqueTogether(
            name='tuitionstructure',
            unique_together=set(),
        ),
        migrations.RemoveField(model_name='tuitionstructure', name='major'),
        migrations.RemoveField(model_name='tuitionstructure', name='degree'),
        migrations.RenameField(
            model_name='tuitionstructure',
            old_name='major_ref',
            new_name='major',
        ),
        migrations.AlterField(
            model_name='tuitionstructure',
            name='major',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tuition_structures',
                to='academics.major',
                verbose_name='رشته',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='tuitionstructure',
            unique_together={('major', 'academic_year')},
        ),
        migrations.AlterModelOptions(
            name='tuitionstructure',
            options={
                'ordering': ['-academic_year', 'major__name'],
                'verbose_name': 'ساختار شهریه',
                'verbose_name_plural': 'ساختار شهریه‌ها',
            },
        ),
        migrations.AlterModelOptions(
            name='studentpayment',
            options={
                'ordering': ['due_date'],
                'verbose_name': 'قسط شهریه پذیرش',
                'verbose_name_plural': 'اقساط شهریه پذیرش',
            },
        ),
        migrations.DeleteModel(name='Tuition'),
        migrations.DeleteModel(name='TuitionHistory'),
    ]
