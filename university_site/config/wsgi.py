import os
from django.core.wsgi import get_wsgi_application

# Local default: config.settings
# On cPanel set env to: config.settings_prod
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
