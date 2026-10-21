# Endpoints de infraestructura: healthchecks (liveness/readiness) y favicon.

from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.templatetags.static import static


def liveness(request):
    return JsonResponse({'status': 'ok'})


def readiness(request):
    try:
        connections['default'].cursor().execute('SELECT 1')
    except OperationalError as exc:
        return JsonResponse({'status': 'error', 'detail': str(exc)}, status=503)
    return JsonResponse({'status': 'ready'})


def favicon(request):
    """/favicon.ico -> PNG estático (lo piden navegadores y bots aunque el HTML declare otro icono)."""
    return HttpResponsePermanentRedirect(static('img/flowly-logo-32.png'))
