import os
import sys

# مسیر ریشه پروژه (همان پوشه‌ای که manage.py داخلش است)
project_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# .env را از ریشه پروژه بخوان
os.chdir(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
