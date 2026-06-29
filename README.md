# Flowly

SaaS de gestión de proyectos multi-tenant (estilo Trello/Asana) con un toque propio:
**La Oficina**, una sala 8-bit donde ves a tu equipo conectado trabajando en sus mesas.

## Stack
Django + plantillas + HTMX + Alpine.js + Tailwind (binario standalone) · PostgreSQL · Docker.
Sin SPA: SSR ágil con islas de interactividad. Tiempo real por *polling* (free-tier friendly).

## Funcionalidades
- Tableros kanban con drag&drop, vistas Lista / Tabla / Calendario.
- Tareas con subtareas, comentarios, multi-asignado, etiquetas y prioridades.
- Organizaciones multi-tenant con temas por marca y por usuario (claro/oscuro).
- Notificaciones, buscador global, "mis tareas", equipo con carga de trabajo.
- Chat de proyecto y por canales · presencia en vivo.
- **La Oficina**: presencia visual 8-bit con personajes personalizables.

## Desarrollo
```bash
python manage.py migrate
python manage.py seed_demo            # usuario demo / demo12345
python manage.py runserver
```
