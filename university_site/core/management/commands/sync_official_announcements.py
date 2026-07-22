"""
هم‌سان‌سازی اخبار/اطلاعیه‌های صفحه اصلی با سایت رسمی aab.ac.ir
Run: python manage.py sync_official_announcements
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from datetime import datetime

try:
    import jdatetime
except ImportError:  # pragma: no cover
    jdatetime = None

from news.models import Category, News


CATEGORIES = [
    ('آموزش', 'amozesh', 'academic', 'fas fa-graduation-cap', 'primary', 1),
    ('دانشجویی و فرهنگی', 'daneshjoei', 'cultural', 'fas fa-users', 'success', 2),
    ('اداری و مالی', 'edari-mali', 'administrative', 'fas fa-file-invoice-dollar', 'warning', 3),
    ('پژوهشی و فناوری', 'pazhohesh', 'research', 'fas fa-flask', 'info', 4),
]


OFFICIAL_ANNOUNCEMENTS = [
    {
        "cat": "academic",
        "title": "قابل توجه پذیرفته شدگان محترم آزمون‌ سراسری سال 1404",
        "summary": "ضمن عرض تبریک و خیرمقدم و آرزوي موفقيت براي كليه‌ پذیرفته شدگان محترم آزمون‌ سراسری ورودي‌ سال‌ 1404 ، بدینوسیله زمان ثبت نام و مدارک مورد نیاز به شرح ذيل اعلام مي‌گردد. - تاريخ ثبت‌نام از پذيرفته شدگان :از روز دوشنبه:…",
        "content": "ضمن عرض تبریک و خیرمقدم و آرزوي موفقيت براي كليه‌ پذیرفته شدگان محترم آزمون‌ سراسری ورودي‌ سال‌ 1404 ، بدینوسیله زمان ثبت نام و مدارک مورد نیاز به شرح ذيل اعلام مي‌گردد. - تاريخ ثبت‌نام از پذيرفته شدگان :از روز دوشنبه: 1404/07/21 لغایت پنج شنبه 1404/07/24 توجه :كليه پذيرفته شدگان مي‌بايست در زمان مقرر براي ثبت‌نام به موسسه محل قبولي خود مراجعه نمايند، بديهي است عدم مراجعه بموقع پذيرفته‌شدگان براي ثبت‌نام، به منزله انصراف از ادامه تحصيل آنان تلقي خواهد شد . - مدارك‌ لازم‌ براي‌ ثبت‌نام‌: 1- اصل مدرك يا گواهي ديپلم متوسطه(پايه داوزدهم نظام جديد آموزشي جديد) با درج بخش و شهرستان محل اخذ مدرك . تبصره: تاریخ اخذ مدرک تحصیلی پایه دوازدهم در هر یک از رشته های تحصیلی برای نیمسال اول باید حداکثر تا پایان 1404/07/31 و برای رشته های تحصیلی پذیرش برای نیمسال دوم باید حداکثر تا تاریخ 1404/11/30 باشد در غیر این صورت قبولی فرد باطل خواهد بود. 2- اصل‌ شناسنامه‌ و كارت ملي و دو سري‌ فتوكپي‌ از تمام‌ صفحات‌ آنها 3- شش‌ قطعه‌ عكس‌ تمام‌ رخ‌ 4×3 تهيه‌ شده‌ در سال‌ جاري‌ 4- مدركي‌ كه‌ وضعيت‌ نظام‌ وظيفه‌ را با توجه‌ به‌ بند «مقررات‌ وظيفه‌ عمومي»‌ دفترچه‌ راهنماي‌ شماره‌ يك‌ آزمون سراسری سال 1404 مشخص می كند (براي‌ برادران‌) توجه: 1- دانشجویان محترمی که تمایل به تقسیط شهریه یا دریافت وام صندوق رفاه دانشجویان وزارت علوم (با سود 4 درصد و بازپرداخت اقساط بعد از فارغ التحصیلی ) را دارند در هنگام ثبت نام به امور دانشجویی مراجعه نمایند. 2- دانشجویان محترم غیربومی که متقاضی خوابگاه می باشند به امور دانشجویی مراجعه نمایند. اطلاعات بیشتر: 01135750084 ، 01135750810 الی 15 -09114141959 \" معاونت آموزشی و تحصیلات تکمیلی \"",
        "jy": 1404,
        "jm": 7,
        "jd": 21,
        "source": "https://www.aab.ac.ir/index.php/12-announcements/482-1404-6",
        "featured": True
    },
    {
        "cat": "academic",
        "title": "قابل توجه پذیرفته شدگان محترم آزمون‌ کارشناسی ارشد سال‌ 1404",
        "summary": "ضمن عرض تبریک و خیر مقدم و آرزوی موفقیت برای کلیه پذیرفته شدگان محترم آزمون ورودی دوره های کارشناسی ارشد سال 1404، بدینوسیله زمان ثبت نام و مدارک مورد نیاز به شرح ذیل اعلام می گردد . - تاریخ ثبت نام از پذیرفته شدگان از…",
        "content": "ضمن عرض تبریک و خیر مقدم و آرزوی موفقیت برای کلیه پذیرفته شدگان محترم آزمون ورودی دوره های کارشناسی ارشد سال 1404، بدینوسیله زمان ثبت نام و مدارک مورد نیاز به شرح ذیل اعلام می گردد . - تاریخ ثبت نام از پذیرفته شدگان از روز سه شنبه 1404/07/15 لغایت پنج شنبه 1404/07/17 . توجه: کلیه پذیرفته شدگان می بایست در زمان مقرر برای ثبت نام به مؤسسه محل قبولی خود مراجعه نمایند، بدیهی است عدم مراجعه به موقع پذیرفته شدگان برای ثبت نام، به منزله انصراف از ادامه تحصیل آنان تلقی خواهد شد . - مدارک لازم برای ثبت نام : ۱ - اصل و یک برگ تصویر مدرک کارشناسی(لیسانس) مورد تایید وزارت علوم، تحقیقات و فناوری یا وزارت بهداشت، درمان و آموزش پزشکی و یا شورای عالی انقلاب فرهنگی که در آن معدل دوره کارشناسی قید شده باشد . ۲ - اصل شناسنامه و کارت ملی و دو سری فتوکپی از تمام صفحات آنها . ۳ - شش قطعه عکس تمام رخ 4*3 تهیه شده در سال جاری ۴- مدرکی که وضعیت نظام وظیفه را با توجه به بند «مقررات وظیفه عمومی» دفترچه راهنمای شماره یک آزمون ورودی دوره های کارشناسی ارشد ناپیوسته سال 1404 مشخص می کند(برای برادران) . توجه : * دانشجویان محترمی که تمایل به تقسیط شهریه یا دریافت وام صندوق رفاه دانشجویان وزارت علوم ( با سود ۴ درصد و بازپرداخت اقساط بعد از فازغ التحصیلی ) را دارند در هنگام ثبت نام به امور دانشجویی مراجعه نمایند . * دانشجویان محترم غیر بومی که متقاضی خوابگاه می باشند به امور دانشجویی مراجعه نمایند . اطلاعات بیشتر: 01135750084، 01135750810 الی 01135750815 - 09114141959-09119113975-09118035983 « معاونت آموزشی و تحصیلات تکمیلی »",
        "jy": 1404,
        "jm": 7,
        "jd": 15,
        "source": "https://www.aab.ac.ir/index.php/12-announcements/481-1404-5",
        "featured": True
    },
    {
        "cat": "academic",
        "title": "قابل توجه پذیرفته شدگان محترم آزمون‌ کاردانی به کارشناسی ناپیوسته سال‌ 1404",
        "summary": "ضمن عرض تبریک و خیرمقدم وآرزوي موفقيت براي كليه‌ پذیرفته شدگان محترم آزمون کاردانی به کارشناسی ناپیوسته سال‌ 1404، زمان ثبت نام و مدارک مورد نیاز به شرح ذيل اعلام مي‌گردد. تاريخ ثبت‌نام از پذيرفته شدگان : از تاریخ…",
        "content": "ضمن عرض تبریک و خیرمقدم وآرزوي موفقيت براي كليه‌ پذیرفته شدگان محترم آزمون کاردانی به کارشناسی ناپیوسته سال‌ 1404، زمان ثبت نام و مدارک مورد نیاز به شرح ذيل اعلام مي‌گردد. تاريخ ثبت‌نام از پذيرفته شدگان : از تاریخ 1404/07/14 لغایت 1404/07/17 توجه: كليه پذيرفته شدگان مي‌بايست در زمان مقرر براي ثبت‌نام به موسسه محل قبولي خود مراجعه نمايند، بديهي است عدم مراجعه بموقع پذيرفته‌شدگان براي ثبت‌نام، به منزله انصراف از ادامه تحصيل آنان تلقي خواهد شد. - مدارك‌ لازم‌ براي‌ ثبت‌نام‌ اصل‌‌ یا گواهی مدرك ‌‌کاردانی (فوق دیپلم) اصل‌ شناسنامه‌ و دو برگ‌ فتوكپي‌ از تمام‌ صفحات‌ آن اصل‌ کارت ملی و دو برگ‌ فتوكپي‌ از پشت و روی آن 6قطعه‌ عكس‌ 4×3 تمام‌ رخ‌ تهيه‌ شده‌ درسال‌جاري‌. داوطلبان‌ مرد لازم‌ است‌ مدركي‌ را كه‌ وضعيت‌ نظام‌ وظيفه‌ آنان‌ را مشخص‌ كند، ارائه‌ نمايند. اطلاعات بیشتر: 01135750084 ، 09114141959 \"معاونت آموزشی و تحصیلات تکمیلی دانشگاه علامه امینی\"",
        "jy": 1404,
        "jm": 7,
        "jd": 14,
        "source": "https://www.aab.ac.ir/index.php/12-announcements/480-1404-4",
        "featured": True
    },
    {
        "cat": "academic",
        "title": "قابل توجه پذیرفته شدگان محترم آزمون‌ کاردانی فنی و حرفه ای سال 1404",
        "summary": "ضمن عرض تبریک و خیرمقدم و آرزوي موفقيت براي كليه‌ پذیرفته شدگان آزمون‌ کاردانی فنی و حرفه ای سال‌ 1404مؤسسه آموزش عالی علامه امینی ،بدینوسیله زمان ثبت نام و مدارک مورد نیاز به شرح ذيل اعلام مي‌گردد. - تاريخ ثبت‌نام از…",
        "content": "ضمن عرض تبریک و خیرمقدم و آرزوي موفقيت براي كليه‌ پذیرفته شدگان آزمون‌ کاردانی فنی و حرفه ای سال‌ 1404مؤسسه آموزش عالی علامه امینی ،بدینوسیله زمان ثبت نام و مدارک مورد نیاز به شرح ذيل اعلام مي‌گردد. - تاريخ ثبت‌نام از پذيرفته شدگان : از تاریخ 1404/07/14 الی 1404/07/17می باشد توجه :كليه پذيرفته شدگان مي‌بايست در زمان مقرر براي ثبت‌نام به موسسه محل قبولي خود مراجعه نمايند، بديهي است عدم مراجعه بموقع پذيرفته‌شدگان براي ثبت‌نام، به منزله انصراف از ادامه تحصيل آنان تلقي خواهد شد. - مدارك‌ لازم‌ براي‌ ثبت‌نام‌ 1- اصل يا گواهي مدرك دیپلم 2- اصل شناسنامه به انضمام 2 نسخه تصوير از تمام صفحات 3- اصل كارت ملي به انضمام دو برگ تصوير پشت و روي 4- 6قطعه ‌عكس ‌تمام‌ رخ ‌4×3 تهيه ‌شده ‌در سالجاري 5- كليه‌ پذيرفته‌شدگان (برادران) مدرکی دال بر مشخص نمودن ‌وضعيت ‌نظام ‌وظيفه اطلاعات بیشتر: 01135750084 ، 09114141959- 01135750810-15 \"معاونت آموزشی و تحصیلات تکمیلی دانشگاه علامه امینی\"",
        "jy": 1404,
        "jm": 7,
        "jd": 14,
        "source": "https://www.aab.ac.ir/index.php/12-announcements/479-1404-3",
        "featured": True
    },
    {
        "cat": "academic",
        "title": "تقویم آموزشی نیمسال اول 1404",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/12-announcements/478-1404-2",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/12-announcements/478-1404-2",
        "jy": 1404,
        "jm": 6,
        "jd": 21,
        "source": "https://www.aab.ac.ir/index.php/12-announcements/478-1404-2",
        "featured": True
    },
    {
        "cat": "academic",
        "title": "زمانبندی انتخاب واحد نیمسال دوم تحصیلی 1405-1404",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/483-1405-1404",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/483-1405-1404",
        "jy": 1405,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/15-announcements/amozesh/483-1405-1404",
        "featured": True
    },
    {
        "cat": "academic",
        "title": "تقویم انتخاب واحد نیمسال دوم تحصیلی 1402-1401",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/427-1402-1402",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/427-1402-1402",
        "jy": 1402,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/15-announcements/amozesh/427-1402-1402",
        "featured": False
    },
    {
        "cat": "academic",
        "title": "تقویم آموزشی نیمسال دوم تحصیلی 1402-1401",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/426-1402-1401",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/426-1402-1401",
        "jy": 1402,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/15-announcements/amozesh/426-1402-1401",
        "featured": False
    },
    {
        "cat": "academic",
        "title": "زمانیندی انتخاب واحد نیمسال دوم تحصیلی 1400",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/411-1400-5",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/411-1400-5",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/15-announcements/amozesh/411-1400-5",
        "featured": False
    },
    {
        "cat": "academic",
        "title": "تقویم آموزشی نیم سال دوم تحصیلی 1400",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/410-1400-4",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/15-announcements/amozesh/410-1400-4",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/15-announcements/amozesh/410-1400-4",
        "featured": False
    },
    {
        "cat": "cultural",
        "title": "ولادت امام خوبی‌ها، علی بن موسی الرضا (ع) تبریک و تهنیت باد",
        "summary": "بر روی رضا شمس امامت صلوات بر شافع ما روز قیامت صلوات در شام ولادتش که شادند همه بفرست بر این روح کرامت صلوات میلاد امام جانان امام هشتم مبارک باد",
        "content": "بر روی رضا شمس امامت صلوات بر شافع ما روز قیامت صلوات در شام ولادتش که شادند همه بفرست بر این روح کرامت صلوات میلاد امام جانان امام هشتم مبارک باد",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/430-2023-05-31-07-12-58",
        "featured": False
    },
    {
        "cat": "cultural",
        "title": "کرسی آزاد اندیشی با موضوع آموزش و پرورش و مسئله سیاست",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/425-2022-11-07-07-20-54",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/425-2022-11-07-07-20-54",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/425-2022-11-07-07-20-54",
        "featured": False
    },
    {
        "cat": "cultural",
        "title": "اطلاعیه مهم امور دانشجویی",
        "summary": "به اطلاع دانشجویان محترم جدیدالورود می رساند: مطابق سنوات گذشته طرح جامع سلامت روان دانشجویان ورودی جدید سال ۱۴۰۰-۱۳۹۹ در مقاطع مختلف در حال اجرا می باشد. کلیه دانشجویان ضمن مراجعه به سامانه سجاد حداکثر تا پایان آذرماه…",
        "content": "به اطلاع دانشجویان محترم جدیدالورود می رساند: مطابق سنوات گذشته طرح جامع سلامت روان دانشجویان ورودی جدید سال ۱۴۰۰-۱۳۹۹ در مقاطع مختلف در حال اجرا می باشد. کلیه دانشجویان ضمن مراجعه به سامانه سجاد حداکثر تا پایان آذرماه نسبت به تکمیل فرم ها اقدام نمایند. لینک آدرس سامانه کارنامه سلامت دانشجویان: http://portal.saorg.ir/mentalhealth معاونت دانشجویی و فرهنگی",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/379-2020-11-09-08-34-59",
        "featured": False
    },
    {
        "cat": "cultural",
        "title": "قابل توجه دانشجویان محترم متقاضی وام دانشجویی",
        "summary": "به اطلاع دانشجویان محترم می رساند جهت استفاده از وام صندوق رفاه دانشجویان وزارت علوم ،با آماده نمودن مدارک لازم، حداکثر تا تاریخ ۹۹/۰۹/۳۰ به سامانه صندوق رفاه دانشجویان به آدرس www.swf.ir مراجعه فرمائید. راهنمای دریافت…",
        "content": "به اطلاع دانشجویان محترم می رساند جهت استفاده از وام صندوق رفاه دانشجویان وزارت علوم ،با آماده نمودن مدارک لازم، حداکثر تا تاریخ ۹۹/۰۹/۳۰ به سامانه صندوق رفاه دانشجویان به آدرس www.swf.ir مراجعه فرمائید. راهنمای دریافت و بازپرداخت وام های دانشجویی در صورت هرگونه سوال با آقای اسماعیلیان تماس حاصل فرمائید. ۰۱۱۳۵۷۵۰۸۱۰ داخلی ۱۰۳ معاونت دانشجویی و فرهنگی",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/378-2020-11-09-08-23-30",
        "featured": False
    },
    {
        "cat": "cultural",
        "title": "ولادت حضرت فاطمه زهرا (س) و روز زن مبارک باد",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/363-2020-02-15-06-59-48",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/363-2020-02-15-06-59-48",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/29-announcements/daneshjoei/363-2020-02-15-06-59-48",
        "featured": False
    },
    {
        "cat": "administrative",
        "title": "اطلاعیه تسویه حساب مالی نیمسال دوم 1401-1400",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/413-1401-1400",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/413-1401-1400",
        "jy": 1401,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/413-1401-1400",
        "featured": False
    },
    {
        "cat": "administrative",
        "title": "اطلاعیه تسویه حساب دانشجویان در نیمسال اول99",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/384-99",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/384-99",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/384-99",
        "featured": False
    },
    {
        "cat": "administrative",
        "title": "متقاضیان وام های تحصیلی",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/343-متقاضیان-وام-های-تحصیلی",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/343-متقاضیان-وام-های-تحصیلی",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/343-متقاضیان-وام-های-تحصیلی",
        "featured": False
    },
    {
        "cat": "administrative",
        "title": "اطلاعیه تسویه حساب ترم 972",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/326-اطلاعیه-تسویه-حساب-ترم-972",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/326-اطلاعیه-تسویه-حساب-ترم-972",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/326-اطلاعیه-تسویه-حساب-ترم-972",
        "featured": False
    },
    {
        "cat": "administrative",
        "title": "بررسی وضعیت مالی نیم سال اول 96",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/280-بررسی-وضعیت-مالی-نیم-سال-اول-96",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/280-بررسی-وضعیت-مالی-نیم-سال-اول-96",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/30-announcements/اداری-و-مالی/280-بررسی-وضعیت-مالی-نیم-سال-اول-96",
        "featured": False
    },
    {
        "cat": "research",
        "title": "جلسات دفاع تاریخ 1401/11/13",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/428-1401-11-13",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/428-1401-11-13",
        "jy": 1401,
        "jm": 11,
        "jd": 13,
        "source": "https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/428-1401-11-13",
        "featured": False
    },
    {
        "cat": "research",
        "title": "اطلاعیه مهم فرهنگی",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/381-2020-11-09-08-36-26",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/381-2020-11-09-08-36-26",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/381-2020-11-09-08-36-26",
        "featured": False
    },
    {
        "cat": "research",
        "title": "قابل توجه دانشجویان محترم کارشناسی ارشد",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/310-قابل-توجه-دانشجویان-محترم-کارشناسی-ارشد",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/310-قابل-توجه-دانشجویان-محترم-کارشناسی-ارشد",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/310-قابل-توجه-دانشجویان-محترم-کارشناسی-ارشد",
        "featured": False
    },
    {
        "cat": "research",
        "title": "وایفا رایگان",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/267-وایفا-رایگان",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/267-وایفا-رایگان",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/267-وایفا-رایگان",
        "featured": False
    },
    {
        "cat": "research",
        "title": "برگزاری کارگاه آموزشی",
        "summary": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/255-برگزاری-کارگاه-آموزشی",
        "content": "متن کامل این اطلاعیه در سایت رسمی موسسه منتشر شده است.\nمنبع: https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/255-برگزاری-کارگاه-آموزشی",
        "jy": 1400,
        "jm": 1,
        "jd": 1,
        "source": "https://www.aab.ac.ir/index.php/31-announcements/پژوهش-و-فناوری/255-برگزاری-کارگاه-آموزشی",
        "featured": False
    }
]


def _to_aware(jy, jm, jd):
    if jdatetime is None:
        return timezone.now()
    try:
        g = jdatetime.date(jy, jm, jd).togregorian()
        dt = datetime(g.year, g.month, g.day, 9, 0, 0)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt)
        return dt
    except Exception:
        return timezone.now()


class Command(BaseCommand):
    help = 'Import official aab.ac.ir homepage announcements into News'

    def handle(self, *args, **options):
        from django.db.models.signals import post_save, pre_save
        from news import signals as news_signals

        # جلوگیری از ارسال انبوه SMS هنگام import
        pre_save.disconnect(news_signals.news_cache_old_published, sender=News)
        post_save.disconnect(news_signals.news_sms_notify, sender=News)
        try:
            self._run_import()
        finally:
            pre_save.connect(news_signals.news_cache_old_published, sender=News)
            post_save.connect(news_signals.news_sms_notify, sender=News)

    def _run_import(self):
        cat_map = {}
        for name, slug, ctype, icon, color, order in CATEGORIES:
            obj, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category_type': ctype,
                    'icon': icon,
                    'color': color,
                    'order': order,
                },
            )
            cat_map[ctype] = obj
            self.stdout.write(f'Category ready: {name}')

        created = updated = 0
        for item in OFFICIAL_ANNOUNCEMENTS:
            title = item['title']
            # MySQL SlugField default max_length=50
            base_slug = slugify(title, allow_unicode=True)[:40] or f'ann-{created + updated + 1}'
            slug = base_slug
            n = 1
            while News.objects.filter(slug=slug).exclude(title=title).exists():
                suffix = f'-{n}'
                slug = f'{base_slug[:50 - len(suffix)]}{suffix}'
                n += 1

            defaults = {
                'slug': slug,
                'category': cat_map.get(item['cat']),
                'news_type': 'announcement',
                'summary': item['summary'][:500],
                'content': item['content'],
                'is_featured': bool(item.get('featured')),
                'is_published': True,
            }
            obj = News.objects.filter(title=title).first()
            if obj:
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
                updated += 1
                action = 'updated'
            else:
                obj = News.objects.create(title=title, **defaults)
                created += 1
                action = 'created'

            pub = _to_aware(item['jy'], item['jm'], item['jd'])
            News.objects.filter(pk=obj.pk).update(published_at=pub)
            self.stdout.write(f'  [{action}] {title[:70]}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. created={created} updated={updated} total={len(OFFICIAL_ANNOUNCEMENTS)}'
        ))
