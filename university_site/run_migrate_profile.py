"""One-shot migrate for profile/photo fields. Safe to delete after run."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.core.management import call_command

call_command('migrate', 'accounts', '0004', verbosity=2)
call_command('migrate', 'admissions', '0008', verbosity=2)
print('MIGRATE_OK')
