"""One-shot: apply migrations then restart Passenger."""
import os
import pathlib
import sys

root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)
os.chdir(root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_prod")

import django
django.setup()

from django.core.management import call_command

print("=== migrate ===")
call_command("migrate", "--noinput")
pathlib.Path("tmp").mkdir(exist_ok=True)
pathlib.Path("tmp/restart.txt").touch()
print("=== done ===")
