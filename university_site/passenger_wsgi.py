import os
import sys

# Deploy ONLY on a separate subdomain/app folder.
# Do NOT place this project inside the main Allameh Amini public_html root.

project_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.chdir(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
