# Flowly

SaaS de gestión de proyectos **multi-tenant** (estilo Trello/Asana) con un toque propio:
**La Oficina**, una sala 8-bit donde ves a tu equipo conectado trabajando en sus mesas.

## Stack

Django · plantillas + **HTMX** + **Alpine.js** · **Tailwind** (binario standalone, sin Node) ·
**PostgreSQL** · Docker. Sin SPA: SSR ágil con islas de interactividad. El "tiempo real"
(presencia, chat, notificaciones) se hace por **polling**, pensado para encajar en planes gratuitos.

## Funcionalidades

- Tableros **kanban** con drag&drop + vistas **Lista / Tabla / Calendario**.
- Tareas con subtareas, comentarios, multi-asignado, etiquetas y prioridades.
- **Organizaciones multi-tenant** con temas por marca y por usuario (claro/oscuro).
- Notificaciones, buscador global con autocompletar, "mis tareas", equipo con carga de trabajo.
- **Chat** de proyecto y por canales · presencia en vivo.
- **La Oficina**: presencia visual 8-bit con personajes personalizables.

## Desarrollo local

```bash
python -m venv .venv && source .venv/bin/activate   # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo            # usuario: demo / demo12345
python manage.py seed_nosolowebs      # (opcional) organización de ejemplo con marca propia
python manage.py runserver
```

> Tailwind: el CSS compilado (`static/css/tailwind.build.css`) es un artefacto de build (gitignored).
> En el contenedor se compila solo; en local:
> `tailwindcss -c tailwind.config.js -i static/css/tailwind.input.css -o static/css/tailwind.build.css --minify`.

## Despliegue en Railway

El repo trae `Dockerfile`, `docker-entrypoint.sh` y `railway.json` listos. El contenedor compila
Tailwind, ejecuta `collectstatic`, aplica `migrate` y arranca gunicorn; el healthcheck es `/healthz`.

1. **New Project → Deploy from GitHub repo** → este repositorio (builder = Dockerfile, ya declarado).
2. **+ New → Database → PostgreSQL** (Railway expone `DATABASE_URL` automáticamente).
3. **Variables** del servicio web:

   | Variable | Valor |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `flowly.settings.production` |
   | `DJANGO_SECRET_KEY` | *(una cadena larga y aleatoria)* |
   | `DATABASE_URL` | *referenciar la del Postgres:* `${{Postgres.DATABASE_URL}}` |

   `ALLOWED_HOSTS` y CSRF se rellenan solos con `RAILWAY_PUBLIC_DOMAIN`. Si usas dominio propio,
   añade `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`.
4. El primer deploy migra solo. Para datos de ejemplo, en la **shell** del servicio:
   `python manage.py seed_demo` (y `seed_nosolowebs`).

### Notas

- **Avatares**: el FS de Railway es efímero, así que las subidas se pierden al redesplegar.
  Persistencia real = follow-up con S3 (django-storages).
- **Notificaciones/chat** viven en la app (sin email; no hay workers).

## Tests

```bash
python manage.py test
```
