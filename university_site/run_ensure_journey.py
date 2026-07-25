"""One-shot runner for cPanel: python run_ensure_journey.py"""
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_prod")

import django
django.setup()

from django.core.management import call_command

print("=== ensure_journey_ready ===")
call_command("ensure_journey_ready", national_id="0602971500")
print("=== done ===")
import pathlib
pathlib.Path("tmp/restart.txt").touch()
