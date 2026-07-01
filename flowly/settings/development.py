# Entorno de desarrollo — Flowly

from .base import *  # noqa: F401, F403

DEBUG = True

# Clave solo-desarrollo: base.py no trae default, así ningún otro entorno
# puede arrancar por accidente con una clave insegura.
if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = 'django-insecure-dev-only-key'

# En desarrollo servimos los estáticos sin hashing de manifest, para que
# `runserver` los sirva directo desde los finders (sin necesitar collectstatic
# ni el manifest de WhiteNoise que sí usa producción).
STORAGES['staticfiles'] = {  # noqa: F405
    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
}

# Servir /media/ (avatares) desde el FS local en desarrollo.
SERVE_MEDIA = True
