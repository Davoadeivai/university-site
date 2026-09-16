"""«بابلسر-بهنمیر» زیر نام موسسه در سربرگ، وسط‌چین."""
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings


class TheBannerShowsTheLocationTests(TestCase):

    def setUp(self):
        cache.clear()

    def _banner(self):
        html = self.client.get(reverse('core:home')).content.decode()
        return html.split('class="bnr-name"')[1].split('bnr-state')[0]

    def test_it_sits_under_the_name(self):
        SiteSettings.objects.get_or_create(pk=1)
        cache.clear()
        banner = self._banner()
        self.assertIn('بابلسر-بهنمیر', banner)
        self.assertLess(banner.index('bnr-fa'), banner.index('bnr-place'))

    def test_the_default_is_babolsar_behnamir(self):
        self.assertEqual(SiteSettings().university_location_fa, 'بابلسر-بهنمیر')

    def test_it_can_be_changed_from_the_panel(self):
        row, _ = SiteSettings.objects.get_or_create(pk=1)
        row.university_location_fa = 'مازندران'
        row.save()
        cache.clear()
        self.assertIn('مازندران', self._banner())

    def test_an_empty_value_hides_the_line(self):
        row, _ = SiteSettings.objects.get_or_create(pk=1)
        row.university_location_fa = ''
        row.save()
        cache.clear()
        self.assertNotIn('bnr-place', self._banner())

    def test_the_name_block_is_centred_in_one_column(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'css' /
               'main.css').read_text(encoding='utf-8')
        # چند قاعده با همین انتخابگر هست؛ آن که چیدمان را تعیین می‌کند
        # همان است که display: flex دارد.
        block = next(chunk.split('}')[0]
                     for chunk in css.split('\n.bnr-name {')[1:]
                     if 'display: flex' in chunk.split('}')[0])
        self.assertIn('flex-direction: column', block)
        self.assertIn('align-items: center', block)
