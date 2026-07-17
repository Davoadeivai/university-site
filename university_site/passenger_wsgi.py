import os
import sys

# Set the path to your project directory (for subdomain deployment)
project_root = '/home/cp29524/public_html/university'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')

# Import Django and set up
import django
django.setup()

# Import WSGI application
from config.wsgi import application

# This application object is used by the development server
# and by any WSGI server configured to use this file.
