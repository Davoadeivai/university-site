"""One-shot: apply dashboard 0005 then restart Passenger."""
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

print("=== migrate dashboard ===")
call_command("migrate", "dashboard", "--noinput")
print("=== ensure journey installment plan ===")
try:
    call_command("ensure_journey_ready")
except Exception as e:
    print("ensure_journey_ready skipped:", e)
pathlib.Path("tmp").mkdir(exist_ok=True)
pathlib.Path("tmp/restart.txt").touch()
print("=== done ===")
