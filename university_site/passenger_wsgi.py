import os
import sys
from urllib.parse import unquote

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.chdir(project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_prod")

from django.core.wsgi import get_wsgi_application

_django_app = get_wsgi_application()


def _to_wsgi_str(value):
    """Convert Unicode path to WSGI latin-1 form expected by Django."""
    return value.encode("utf-8").decode("iso-8859-1")


def _fix_path_info(path):
    """
    LiteSpeed/Passenger may leave Persian URLs percent-encoded in PATH_INFO,
    so Django cannot match routes like /درباره-ما/ and returns 404.
    """
    if not path:
        return "/"

    if "%" in path:
        path = unquote(path, encoding="utf-8", errors="replace")

    try:
        path.encode("ascii")
        return path
    except UnicodeEncodeError:
        pass

    # Already WSGI-mangled UTF-8 bytes → leave for Django
    try:
        recovered = path.encode("iso-8859-1").decode("utf-8")
        if recovered != path:
            return path
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Real Unicode path → WSGI form
    return _to_wsgi_str(path)


def application(environ, start_response):
    environ["PATH_INFO"] = _fix_path_info(environ.get("PATH_INFO", "/"))
    script_name = environ.get("SCRIPT_NAME")
    if script_name:
        environ["SCRIPT_NAME"] = _fix_path_info(script_name)
    return _django_app(environ, start_response)
