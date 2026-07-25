"""Migrate + rebuild tuition installments. One-shot for cPanel."""
import os
import sys

root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)
os.chdir(root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_prod")

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from dashboard.models import Payment, Semester
from dashboard.onboarding import ensure_tuition_invoice

print("=== migrate ===")
call_command("migrate", "dashboard", "0004", "--noinput")
print("=== rebuild invoices ===")
sem = Semester.objects.filter(is_active=True).first()
for user in User.objects.filter(profile__role="student"):
    # convert legacy single pending tuition into 3 installments
    ensure_tuition_invoice(user, sem)
    print("user", user.username, "ok")
print("=== done ===")
import pathlib
pathlib.Path("tmp/restart.txt").touch()
