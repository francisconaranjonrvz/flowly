"""
ASGI config for Flowly.

Exposes the ASGI callable for async-capable servers.
Not required for this project's scope but included for completeness
and future extensibility (e.g., WebSocket support for real-time updates).
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flowly.settings.production')
application = get_asgi_application()
