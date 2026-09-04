"""صفحه‌های عمومی بانک اطلاعات موسسه."""
from __future__ import annotations

from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.urls import reverse
from django.shortcuts import get_object_or_404, render

from .models import CurriculumDocument, DirectoryPerson, ExternalResource


def staff_directory(request):
    """دفترچهٔ تلفن و مسئولان — یک صفحه، قابل جست‌وجو از سمت کاربر."""
    query = (request.GET.get('q') or '').strip()

    people = DirectoryPerson.objects.filter(category='staff', is_active=True)
    if query:
        people = people.filter(
            Q(full_name__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(position__icontains=query)
            | Q(extension__icontains=query)
        )

    return render(request, 'directory/staff.html', {
        'people': people,
        'query': query,
        'total': DirectoryPerson.objects.filter(
            category='staff', is_active=True).count(),
    })


# ارکان و اعضای موسسه — هر کدام با نشانی و صفحهٔ خودش.
#
# پیش از این همه در یک صفحه بودند و منو با لنگر (#founder) به میانهٔ
# همان صفحه می‌پرید: هیئت مؤسس و هیئت امنا و هیئت علمی و مدرسین، همه
# زیر یک عنوان. حالا هر رکن نشانی مستقل دارد و صفحه‌اش فقط خودش را
# نشان می‌دهد.
#
# (نشانی, کلید دسته, عنوان, آیکون, یک‌جمله معرفی)
PEOPLE_SECTIONS = [
    ('هیات-موسس', 'founder', 'هیئت مؤسس', 'fa-landmark',
     'بنیان‌گذاران موسسه؛ اساسنامه و خط‌مشی بلندمدت از این رکن می‌آید.'),
    ('هیات-امنا', 'trustee', 'هیئت امنا', 'fa-users-gear',
     'بالاترین رکن سیاست‌گذاری موسسه؛ بودجه و تشکیلات اینجا تصویب می‌شود.'),
    ('هیات-علمی', 'faculty', 'اعضای هیئت علمی', 'fa-user-graduate',
     'استادان موسسه، به تفکیک رشته و مدرک.'),
    ('مدیران-گروه', 'group_head', 'مدیران گروه آموزشی', 'fa-sitemap',
     'مدیر هر گروه آموزشی و حوزهٔ کاری‌اش.'),
    ('مدرسین', 'lecturer', 'مدرسین', 'fa-chalkboard-user',
     'مدرسان همکار موسسه.'),
]


def _people_group(key, label, icon):
    members = list(
        DirectoryPerson.objects.filter(category=key, is_active=True))
    return {'key': key, 'label': label, 'icon': icon, 'members': members}


def academic_people(request):
    """فهرست کامل — همهٔ ارکان و اعضا، با لینک به صفحهٔ هرکدام."""
    groups = []
    for slug, key, label, icon, _blurb in PEOPLE_SECTIONS:
        group = _people_group(key, label, icon)
        if group['members']:
            group['url'] = reverse('directory:people_section', args=[slug])
            groups.append(group)

    return render(request, 'directory/people.html', {
        'groups': groups,
        'sections': PEOPLE_SECTIONS,
    })


def academic_people_section(request, slug):
    """یک رکن، در صفحهٔ خودش."""
    row = next((item for item in PEOPLE_SECTIONS if item[0] == slug), None)
    if row is None:
        raise Http404('چنین بخشی نیست.')

    _slug, key, label, icon, blurb = row
    group = _people_group(key, label, icon)
    others = [
        {'slug': other[0], 'label': other[2], 'icon': other[3]}
        for other in PEOPLE_SECTIONS if other[0] != slug
    ]
    return render(request, 'directory/people_section.html', {
        'group': group,
        'label': label,
        'icon': icon,
        'blurb': blurb,
        'others': others,
        'page_title': label,
    })


def curriculum_list(request):
    """سرفصل‌های مصوب، گروه‌بندی‌شده بر اساس مقطع."""
    query = (request.GET.get('q') or '').strip()
    level = (request.GET.get('level') or '').strip()

    docs = CurriculumDocument.objects.filter(is_active=True).select_related('major')
    if query:
        docs = docs.filter(Q(title__icontains=query) | Q(note__icontains=query))
    if level:
        docs = docs.filter(level=level)

    # شمارش هر مقطع برای فیلترهای بالای صفحه — یک کوئری، نه یکی به ازای دکمه
    counts = dict(
        CurriculumDocument.objects.filter(is_active=True)
        .values_list('level')
        .annotate(n=Count('id'))
    )

    # آیا فایل واقعاً روی دیسک هست؟
    #
    # هر ۷۵ سند در دیتابیس نام فایل دارند ولی فایلشان روی سرور نیست،
    # و کارت هرکدام یک لینک دانلود بود: بازدیدکننده کلیک می‌کرد و به
    # صفحهٔ ۴۰۴ می‌رسید. کارتی که فایلش نیست، دیگر لینک نمی‌شود.
    #
    # یک stat به‌ازای هر سند است، نه یک کوئری؛ برای این تعداد ناچیز
    # است و جای درستش همین‌جاست تا قالب تصمیم نگیرد.
    def has_file(doc):
        if not doc.file:
            return False
        try:
            return doc.file.storage.exists(doc.file.name)
        except (OSError, ValueError, NotImplementedError):
            return False

    grouped = []
    for key, label in CurriculumDocument.LEVEL_CHOICES:
        items = [{'doc': d, 'ready': has_file(d)}
                 for d in docs if d.level == key]
        if items:
            grouped.append({'key': key, 'label': label, 'items': items,
                            'missing': sum(1 for i in items if not i['ready'])})

    # فقط مقطع‌هایی که واقعاً سندی دارند دکمهٔ فیلتر می‌گیرند — وگرنه
    # کاربر روی «کاردانی ناپیوسته» می‌زند و به صفحهٔ خالی می‌رسد.
    level_options = [
        {'key': key, 'label': label, 'count': counts[key]}
        for key, label in CurriculumDocument.LEVEL_CHOICES
        if counts.get(key)
    ]

    return render(request, 'directory/curricula.html', {
        'grouped': grouped,
        'level_options': level_options,
        'query': query,
        'active_level': level,
        'total': sum(counts.values()),
    })


def curriculum_download(request, pk: int):
    """دانلود سرفصل با شمارش.

    فایل مستقیم از استوریج سرو می‌شود تا شمارنده معنا داشته باشد؛
    لینک مستقیم به media/ هیچ‌وقت شمرده نمی‌شد.
    """
    doc = get_object_or_404(CurriculumDocument, pk=pk, is_active=True)
    if not doc.file:
        raise Http404('فایلی برای این سرفصل ثبت نشده است.')

    # update با F ساده‌تر بود ولی save() اندازهٔ فایل را هم دوباره حساب
    # می‌کند؛ اینجا فقط شمارنده لازم است.
    CurriculumDocument.objects.filter(pk=doc.pk).update(
        download_count=doc.download_count + 1)

    try:
        handle = doc.file.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('فایل روی سرور پیدا نشد.')

    return FileResponse(
        handle, as_attachment=True,
        filename='%s.pdf' % doc.title,
        content_type='application/pdf',
    )


def resources(request):
    """پایگاه‌ها و سامانه‌های بیرونی."""
    groups = []
    for key, label in ExternalResource.CATEGORY_CHOICES:
        items = list(ExternalResource.objects.filter(
            category=key, is_active=True))
        if items:
            groups.append({'label': label, 'items': items})

    return render(request, 'directory/resources.html', {'groups': groups})
