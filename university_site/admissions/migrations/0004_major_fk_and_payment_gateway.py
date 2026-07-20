import django.db.models.deletion
from django.db import migrations, models


def forwards_map_majors(apps, schema_editor):
    Application = apps.get_model('admissions', 'Application')
    Major = apps.get_model('academics', 'Major')
    majors = list(Major.objects.all())
    by_name = {}
    for m in majors:
        by_name.setdefault(m.name.strip(), m)

    fallback = majors[0] if majors else None
    if fallback is None:
        # بدون رشته نمی‌توان Application موجود را نگه داشت
        return

    for app in Application.objects.all():
        name1 = (app.desired_major_old or '').strip()
        name2 = (app.desired_major2_old or '').strip()
        m1 = by_name.get(name1)
        if not m1:
            # تطبیق تقریبی
            for m in majors:
                if name1 and name1 in m.name:
                    m1 = m
                    break
        if not m1:
            m1 = fallback
        m2 = by_name.get(name2) if name2 else None
        if name2 and not m2:
            for m in majors:
                if name2 in m.name:
                    m2 = m
                    break
        app.desired_major_id = m1.pk
        app.desired_major2_id = m2.pk if m2 else None
        app.save(update_fields=['desired_major_id', 'desired_major2_id'])


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0003_major_group_and_degree_types'),
        ('admissions', '0003_unify_tuition_otp'),
    ]

    operations = [
        migrations.RenameField(
            model_name='application',
            old_name='desired_major',
            new_name='desired_major_old',
        ),
        migrations.RenameField(
            model_name='application',
            old_name='desired_major2',
            new_name='desired_major2_old',
        ),
        migrations.AddField(
            model_name='application',
            name='desired_major',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='applications_priority1',
                to='academics.major',
                verbose_name='اولویت اول رشته',
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='desired_major2',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='applications_priority2',
                to='academics.major',
                verbose_name='اولویت دوم رشته',
            ),
        ),
        migrations.RunPython(forwards_map_majors, backwards_noop),
        migrations.AlterField(
            model_name='application',
            name='desired_major',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='applications_priority1',
                to='academics.major',
                verbose_name='اولویت اول رشته',
            ),
        ),
        migrations.RemoveField(
            model_name='application',
            name='desired_major_old',
        ),
        migrations.RemoveField(
            model_name='application',
            name='desired_major2_old',
        ),
    ]
