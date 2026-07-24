"""
اجرای این فایل: از Terminal cPanel
  python run_migrate.py

یا از طریق SSH:
  cd ~/apps/university_site && python run_migrate.py
"""
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_prod")

import django
django.setup()

from django.core.management import call_command

print("=== شروع migrate ===")
call_command("migrate", "--run-syncdb")
print("=== migrate تمام شد ===")

print("=== collectstatic ===")
call_command("collectstatic", "--noinput")
print("=== collectstatic تمام شد ===")

# restart passenger
import pathlib
pathlib.Path("tmp/restart.txt").touch()
print("=== restart.txt لمس شد — سایت ری‌استارت می‌شود ===")
