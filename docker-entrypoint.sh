#!/bin/sh
# Entrypoint del contenedor: espera la BD, aplica migraciones y arranca.

set -e

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os, socket, time, sys
from urllib.parse import urlparse

url = os.environ.get('DATABASE_URL', '').strip()
p = urlparse(url)
host = p.hostname or 'localhost'
port = p.port or 5432
print(f'Waiting for PostgreSQL at {host}:{port}...', flush=True)
deadline = time.time() + 90
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            sys.exit(0)
    except OSError:
        time.sleep(1)
print(f'Database at {host}:{port} not reachable after 90s', file=sys.stderr)
sys.exit(1)
PY

echo "Applying database migrations..."
python manage.py migrate --noinput

exec "$@"
