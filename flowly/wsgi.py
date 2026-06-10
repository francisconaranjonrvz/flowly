"""
WSGI config for Flowly.

Exposes the WSGI callable as a module-level variable named ``application``.
Used by production servers (Gunicorn, uWSGI) to serve the application.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flowly.settings.production')
application = get_wsgi_application()
