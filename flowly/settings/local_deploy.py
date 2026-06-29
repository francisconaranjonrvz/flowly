# Despliegue LOCAL (NO es producción real).
# Hereda de production.py (DEBUG off, WhiteNoise + manifest, gunicorn-like)
# pero relaja lo que impide servir por http://localhost (TLS/cookies seguras).
# Útil para levantar la app en local con un servidor WSGI real (waitress).

import os

# production.py exige DJANGO_SECRET_KEY; aquí inyectamos una clave fija local
# ANTES de importarlo para que el arranque local no requiera variables.
os.environ.setdefault('DJANGO_SECRET_KEY', 'local-deploy-insecure-key-not-for-production')

from .production import *  # noqa: E402, F401, F403

DEBUG = False

# Sin HTTPS en local: desactivar redirección y cookies "secure".
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Clave fija solo para uso local (no usar en producción).
SECRET_KEY = 'local-deploy-insecure-key-not-for-production'

# Servir /media/ (avatares) desde el FS local: aquí DEBUG=False, así que
# django.views.static.serve (vía SERVE_MEDIA en urls.py) hace el trabajo.
SERVE_MEDIA = True
