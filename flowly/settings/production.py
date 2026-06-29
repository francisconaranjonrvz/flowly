# Entorno de producción — Flowly (Railway)

from .base import *  # noqa: F401, F403

DEBUG = False

# En producción el SECRET_KEY es OBLIGATORIO: sin fallback inseguro. Si la
# variable de entorno no está definida, el arranque falla de forma explícita
# (mejor que servir con una clave pública conocida).
SECRET_KEY = env('DJANGO_SECRET_KEY')  # noqa: F405

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int('DJANGO_HSTS_SECONDS', default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Medios (avatares): el FS de Railway es efímero, así que NO servimos /media/
# desde disco (SERVE_MEDIA queda en False, heredado de base). Persistencia real
# = follow-up: django-storages + S3 (STORAGES['default'] -> S3Boto3Storage,
# MEDIA_URL apuntando al bucket/CDN).

# Railway expone el dominio público en RAILWAY_PUBLIC_DOMAIN: lo añadimos solo
# a hosts y orígenes CSRF de confianza para que el deploy funcione sin tener
# que configurar el dominio a mano.
_railway_domain = env('RAILWAY_PUBLIC_DOMAIN', default='')
if _railway_domain:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _railway_domain]
    CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, f'https://{_railway_domain}']
