# Endpoints de healthcheck (liveness y readiness).

from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def liveness(request):
    return JsonResponse({'status': 'ok'})


def readiness(request):
    try:
        connections['default'].cursor().execute('SELECT 1')
    except OperationalError as exc:
        return JsonResponse({'status': 'error', 'detail': str(exc)}, status=503)
    return JsonResponse({'status': 'ready'})
