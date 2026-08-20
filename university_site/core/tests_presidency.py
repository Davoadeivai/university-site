"""صفحهٔ ریاست موسسه — چیدمان تازه، نشانی‌های علمی، و کارت تماس."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import PresidencyOffice


class PresidencyPageTests(TestCase):
    """آنچه صفحه باید نشان دهد — و آنچه نباید."""

    @classmethod
    def setUpTestData(cls):
        cls.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_title='دانشیار مدیریت صنعتی',
            president_message='دانشگاه جایی برای ساختن است.',
            president_bio='متن معرفی.',
            president_education='دکتری مدیریت صنعتی\nکارشناسی ارشد صنایع',
            president_resume='رئیس موسسه\nمدیر گروه صنایع',
            president_research='مدیریت زنجیره تأمین\nتولید ناب',
            president_email='president@portal.aab.ac.ir',
            president_phone='01135333333',
            president_website='https://WCM-Society.Com',
            president_website_label='انجمن مدیریت زنجیره تأمین',
            president_orcid='0000-0002-1825-0097',
            office_address='بابلسر، خیابان شهید بهشتی',
            office_hours='شنبه تا چهارشنبه ۸ تا ۱۴',
        )

    def test_page_opens(self):
        res = self.client.get(reverse('core:presidency'))
        self.assertEqual(res.status_code, 200)

    def test_hero_carries_the_name(self):
        html = self.client.get(reverse('core:presidency')).content.decode()
        self.assertIn('pres-hero', html)
        self.assertIn('دکتر حسن فارسیجانی', html)

    def test_multiline_history_becomes_a_list(self):
        """دو خط سابقه باید دو <li> شود، نه یک پاراگراف چسبیده."""
        html = self.client.get(reverse('core:presidency')).content.decode()
        block = html.split('id="education"')[1].split('</article>')[0]
        self.assertEqual(block.count('<li>'), 2)

    def test_website_is_linked_and_safe(self):
        html = self.client.get(reverse('core:presidency')).content.decode()
        self.assertIn('https://WCM-Society.Com', html)
        self.assertIn('انجمن مدیریت زنجیره تأمین', html)
        # بدون noopener، صفحهٔ مقصد می‌تواند تب ما را جای دیگری ببرد
        self.assertIn('rel="noopener noreferrer"', html)

    def test_structured_data_is_valid_json(self):
        import json
        html = self.client.get(reverse('core:presidency')).content.decode()
        # base.html خودش یک بلوک CollegeOrUniversity دارد و اول صفحه
        # می‌آید؛ بلوک این صفحه را باید از میان همه پیدا کرد.
        blocks = [chunk.split('</script>')[0]
                  for chunk in html.split('application/ld+json">')[1:]]
        people = [json.loads(b) for b in blocks
                  if '"Person"' in b]
        self.assertEqual(len(people), 1, 'بلوک Person پیدا نشد')
        self.assertEqual(people[0]['name'], 'دکتر حسن فارسیجانی')
        self.assertIn('worksFor', people[0])

    def test_orcid_becomes_a_full_url(self):
        self.assertEqual(self.office.orcid_url,
                         'https://orcid.org/0000-0002-1825-0097')

    def test_label_falls_back_to_the_domain(self):
        self.office.president_website_label = ''
        self.assertEqual(self.office.website_label, 'WCM-Society.Com')

    def test_empty_lines_are_dropped(self):
        self.office.president_education = 'دکتری\n\n  \nکارشناسی'
        self.assertEqual(self.office.education_list, ['دکتری', 'کارشناسی'])

    def test_page_survives_an_empty_record(self):
        """هیچ فیلدی اجباری نیست؛ صفحه نباید با رکورد خالی بترکد."""
        PresidencyOffice.objects.all().delete()
        PresidencyOffice.objects.create()
        res = self.client.get(reverse('core:presidency'))
        self.assertEqual(res.status_code, 200)


class PresidencyVCardTests(TestCase):
    """کارت تماس باید فایلی بدهد که گوشی بازش کند."""

    def setUp(self):
        self.office = PresidencyOffice.objects.create(
            president_name='دکتر حسن فارسیجانی',
            president_title='دانشیار مدیریت صنعتی',
            president_phone='01135333333',
            president_email='president@portal.aab.ac.ir',
            office_address='بابلسر، خیابان شهید بهشتی',
        )

    def test_download_is_a_vcard(self):
        res = self.client.get(reverse('core:presidency_vcard'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/vcard', res['Content-Type'])
        self.assertIn('attachment', res['Content-Disposition'])

    def test_body_has_the_required_fields(self):
        body = self.client.get(
            reverse('core:presidency_vcard')).content.decode('utf-8')
        self.assertTrue(body.startswith('BEGIN:VCARD'))
        self.assertIn('VERSION:3.0', body)
        self.assertIn('FN:دکتر حسن فارسیجانی', body)
        self.assertIn('01135333333', body)
        self.assertTrue(body.rstrip().endswith('END:VCARD'))

    def test_lines_end_with_crlf(self):
        """بعضی گوشی‌ها فایل با \\n تنها را رد می‌کنند."""
        body = self.client.get(
            reverse('core:presidency_vcard')).content.decode('utf-8')
        self.assertIn('\r\n', body)

    def test_separators_inside_a_value_are_escaped(self):
        """کاما و سمی‌کالن لاتین، فیلد vCard را نصف می‌کنند.

        کاماى فارسى (،) جداکنندهٔ vCard نیست و نباید دست بخورد — یک
        نشانى فارسى معمولى اصلاً به فرار نیاز ندارد. فرار فقط براى
        نویسه‌هاى لاتین لازم است، که در نشانى‌هاى دوزبانه پیش مى‌آید.
        """
        from core import vcard
        self.office.office_address = 'Babolsar, Beheshti St; No. 12'
        body = vcard.build(self.office)
        line = [x for x in body.splitlines() if x.startswith('ADR')][0]
        self.assertIn(r'\,', line)
        self.assertIn(r'\;', line.split('ADR;TYPE=WORK:')[1])

    def test_persian_comma_is_left_alone(self):
        from core import vcard
        self.office.office_address = 'بابلسر، خیابان شهید بهشتی'
        body = vcard.build(self.office)
        self.assertIn('بابلسر، خیابان شهید بهشتی', body)

    def test_missing_record_is_a_404_not_a_crash(self):
        PresidencyOffice.objects.all().delete()
        res = self.client.get(reverse('core:presidency_vcard'))
        self.assertEqual(res.status_code, 404)


class PresidentLinksCommandTests(TestCase):
    """دستور باید در هر دیپلوی بی‌خطر باشد."""

    def test_it_fills_an_empty_field(self):
        PresidencyOffice.objects.create(president_name='رئیس')
        call_command('set_president_links', stdout=StringIO())
        office = PresidencyOffice.objects.first()
        self.assertEqual(office.president_website, 'https://WCM-Society.Com')

    def test_it_leaves_an_admin_edit_alone(self):
        PresidencyOffice.objects.create(
            president_name='رئیس', president_website='https://elsewhere.ir')
        call_command('set_president_links', stdout=StringIO())
        self.assertEqual(PresidencyOffice.objects.first().president_website,
                         'https://elsewhere.ir')

    def test_replace_overrides_on_request(self):
        PresidencyOffice.objects.create(
            president_name='رئیس', president_website='https://elsewhere.ir')
        call_command('set_president_links', '--replace', stdout=StringIO())
        self.assertEqual(PresidencyOffice.objects.first().president_website,
                         'https://WCM-Society.Com')

    def test_no_record_is_reported_not_crashed(self):
        out = StringIO()
        call_command('set_president_links', stdout=out)
        self.assertIn('وجود ندارد', out.getvalue())


class PresidencyAdminTests(TestCase):
    """هر چیزی که روی صفحه دیده می‌شود باید در ادمین قابل ویرایش باشد."""

    def test_every_president_field_is_in_a_fieldset(self):
        from core.admin import PresidencyOfficeAdmin
        listed = set()
        for _title, opts in PresidencyOfficeAdmin.fieldsets:
            listed.update(opts['fields'])
        for field in ('president_website', 'president_website_label',
                      'president_scholar', 'president_orcid',
                      'president_research', 'president_cv'):
            self.assertIn(field, listed, '%s در ادمین دیده نمی‌شود' % field)


class HeroNeverCropsTests(TestCase):
    """قاب عکس رئیس نباید هیچ بخشی از تصویر را ببرد.

    نسخهٔ اول با cover و object-position ثابت ساخته شده بود. عکسی
    که موسسه آپلود کرد عمودی بود و سوژه در نیمهٔ پایین؛ نتیجه این شد
    که فقط دیوار و پرده دیده می‌شد و رئیس اصلاً در قاب نبود. هر عدد
    ثابتی برای یکی از دو نسبت تصویر غلط از آب درمی‌آید، پس تصویر
    اصلی همیشه contain است و پس‌زمینه با نسخهٔ مات پر می‌شود.
    """

    def _css(self):
        from pathlib import Path
        from django.conf import settings
        return (Path(settings.BASE_DIR) / 'static' / 'css' / 'main.css').read_text(
            encoding='utf-8')

    def _rule(self, selector):
        css = self._css()
        start = css.index(selector + ' {')
        return css[start:css.index('}', start)]

    def test_main_photo_is_contained(self):
        rule = self._rule('.pres-hero-img')
        self.assertIn('object-fit: contain', rule)
        self.assertNotIn('cover', rule,
                         'قاب دوباره برش می‌زند')

    def test_the_frame_fills_the_screen(self):
        """قاب باید تمام ارتفاع دیدنی را بگیرد، نه یک عدد ثابت."""
        rule = self._rule('.pres-hero')
        self.assertIn('svh', rule)
        # vh روی موبایل نوار آدرس را هم حساب می‌کند و پایین قاب را
        # زیر نوار می‌برد
        self.assertNotIn('100vh', rule)

    def test_backdrop_fills_the_frame(self):
        rule = self._rule('.pres-hero-wash')
        self.assertIn('object-fit: cover', rule)
        # بدون بزرگ‌نمایی، blur لبه‌ها را شفاف می‌کند و یک نوار روشن
        # دور قاب می‌ماند
        self.assertIn('scale(', rule)

    def test_the_page_renders_without_a_photo(self):
        """رکورد بدون عکس نباید قاب را بشکند."""
        PresidencyOffice.objects.create(president_name='دکتر تست')
        html = self.client.get(reverse('core:presidency')).content.decode()
        self.assertEqual(html.count('pres-hero-wash'), 0)
        self.assertIn('pres-hero-placeholder', html)

    def test_the_entrance_animation_is_opt_out(self):
        """انیمیشن باید داخل prefers-reduced-motion باشد، نه بیرونش."""
        css = self._css()
        before = css[:css.index('.pres-hero-img { animation')]
        guard = before.rindex('@media')
        self.assertIn('prefers-reduced-motion: no-preference',
                      before[guard:guard + 60])

    def test_the_website_shows_as_a_latin_url(self):
        """نشانی باید خودش دیده شود، لاتین و چپ‌به‌راست."""
        PresidencyOffice.objects.create(
            president_name='دکتر تست',
            president_website='https://WCM-Society.Com')
        html = self.client.get(reverse('core:presidency')).content.decode()
        plate = html.split('pres-hero-plate')[1].split('</header>')[0]
        self.assertIn('https://WCM-Society.Com', plate)
        self.assertIn('dir="ltr"', plate)
