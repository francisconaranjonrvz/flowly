# Entorno de desarrollo — Flowly

from .base import *  # noqa: F401, F403

DEBUG = True

# En desarrollo servimos los estáticos sin hashing de manifest, para que
# `runserver` los sirva directo desde los finders (sin necesitar collectstatic
# ni el manifest de WhiteNoise que sí usa producción).
STORAGES['staticfiles'] = {  # noqa: F405
    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
}

# Servir /media/ (avatares) desde el FS local en desarrollo.
SERVE_MEDIA = True
