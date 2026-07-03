# Flowly

**A multi-tenant project management SaaS** (Trello/Asana-style) built solo, end-to-end, on Django — with a differentiator of its own: **The Office**, a live 8-bit room where you see your teammates working at their desks in real time.

[![Live Demo](https://img.shields.io/badge/demo-live-6366f1?style=flat-square)](https://flowly-production-7876.up.railway.app)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/tests-94%20passing-22c55e?style=flat-square)](#testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

**[→ Try the live demo](https://flowly-production-7876.up.railway.app)** — user `demo` / password `demo12345`

---

<!--
Screenshots: drop 4 PNGs into docs/screenshots/ with these exact names, then
uncomment the table below.
  - dashboard.png   → home page ("Mis tableros"), desktop width
  - board.png       → a kanban board with a few cards ("Hoja de Ruta TFG")
  - office.png      → /office/ ("La Oficina") with a couple of characters
  - board-nsw.png   → any board after switching to the NoSoloWebs org (lime theme)
Suggested capture: 1440x900, demo/demo12345 on the local dev server.

## Screenshots

| Dashboard | Kanban board |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Kanban board](docs/screenshots/board.png) |

| The Office (live presence) | Alternate brand & theme |
|---|---|
| ![The Office](docs/screenshots/office.png) | ![NoSoloWebs brand](docs/screenshots/board-nsw.png) |

*(Two organizations shown above — Flowly's indigo brand and a fully re-themed "NoSoloWebs" tenant — same codebase, zero per-tenant code.)*
-->

## Why this project

Flowly started as a single-user Kanban board (a school capstone project) and was rebuilt from the ground up into a real multi-tenant SaaS: organizations, per-tenant branding, roles, invites, and a product surface wide enough to actually run a small team's work — boards, tasks, calendar, chat, notifications, search, and a presence system with a bit of personality.

It's a solo project, built and iterated in structured phases with a clear paper trail of decisions (see commit history), and deployed to a real environment on a real free-tier budget — which forced deliberate architecture choices instead of reaching for the "obvious" tool for every job (see [Engineering highlights](#engineering-highlights)).

## Engineering highlights

- **Multi-tenancy from the data layer up**: every board, task, channel and invite is scoped to an `Organization` through a session-bound active-tenant middleware — not a bolted-on filter. Two demo tenants (Flowly indigo, NoSoloWebs lime) run on the same schema with fully independent branding.
- **Real-time UX without WebSockets, on purpose**: the target infra is free-tier (no Redis/Channels budget), so live chat, notifications, presence, and board updates use **HTMX polling with drag/focus guards** — a deliberate trade-off, not a missing feature. Documented in-code where it matters.
- **Theming as data, not per-brand CSS files**: brand + light/dark mode are CSS custom-property sets selected via `data-brand`/`data-theme` attributes, with an anti-FOUC boot script and per-user overrides layered over per-org defaults.
- **Token-driven design system**: no hardcoded colors in templates — semantic Tailwind tokens (`bg-surface`, `text-on-primary`, …) map to CSS variables, so a new brand is a token block, not a redesign.
- **Server-rendered, HTMX/Alpine islands** — no SPA, no build-heavy JS toolchain (Tailwind ships as a standalone binary, no Node in the image), fast TTFB, small attack surface.
- **94 tests** covering permissions/tenant isolation, view flows, and model behavior; every feature phase shipped behind `manage.py test` passing before merge.

## Features

- **Boards & tasks** — Kanban with drag & drop, plus List / Table / Calendar views of the same data; subtasks with progress, comments, multiple assignees, labels, priorities and due dates.
- **Workspaces** — create organizations from the UI, invite teammates by shareable link (token-based, regenerable), role-based access (owner/manager/member).
- **Live-ish collaboration** — project chat with channels, @mentions, real notifications (not a placeholder bell), global search with autocomplete, cross-board "My tasks" view.
- **The Office** — an opt-in 8-bit presence room: customizable pixel characters, live status ("working" / "away" / custom message), who's-online at a glance.
- **Theming** — brand (Flowly / custom tenant) × mode (light/dark), selectable per-user, defaulting from the organization.
- **Fully responsive** — collapsible sidebar/drawer navigation, mobile agenda view for the calendar, touch-friendly kanban.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Django 4.2, PostgreSQL |
| Frontend | Django templates + **HTMX** + **Alpine.js** (server-rendered, no SPA) |
| Styling | **Tailwind CSS** (standalone binary, no Node toolchain) + a CSS custom-property design-token system |
| "Real-time" | HTMX polling (chat ~4s, notifications ~60s, kanban ~6s) with interaction guards — no WebSockets/Redis needed |
| Auth & sessions | Django's built-in auth, session-based active-organization switching |
| Deployment | Docker → Railway (gunicorn + WhiteNoise), healthchecked (`/healthz`, `/readyz`) |
| Tests | Django `TestCase`, 94 tests |

## Architecture at a glance

```
Organization (tenant)
 ├─ Membership (role: owner / manager / member)
 ├─ Board ── Column ── Card ── Subtask / Comment / Label / Assignees
 ├─ Channel ── Message                (project chat)
 ├─ Notification                      (in-app, polling badge)
 └─ Invite (token)                    (join-by-link)

Request → OrganizationMiddleware (resolves active tenant from session)
        → view (permission-checked against tenant + role)
        → template (brand/theme resolved via context processor)
```

## Local development

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo            # user: demo / demo12345
python manage.py seed_nosolowebs      # (optional) second tenant with its own brand
python manage.py runserver
```

> Tailwind's compiled CSS (`static/css/tailwind.build.css`) is a build artifact (gitignored) — the container builds it automatically; locally:
> `tailwindcss -c tailwind.config.js -i static/css/tailwind.input.css -o static/css/tailwind.build.css --minify`.

## Deployment (Railway)

The repo ships with `Dockerfile`, `docker-entrypoint.sh` and `railway.json`. The container builds Tailwind, runs `collectstatic`, applies migrations, and starts gunicorn; the healthcheck is `/healthz`.

1. **New Project → Deploy from GitHub repo** → this repository (builder = Dockerfile, already declared).
2. **+ New → Database → PostgreSQL** (Railway exposes `DATABASE_URL` automatically).
3. **Environment variables** on the web service:

   | Variable | Value |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `flowly.settings.production` |
   | `DJANGO_SECRET_KEY` | *(a long random string)* |
   | `DATABASE_URL` | reference the Postgres service: `${{Postgres.DATABASE_URL}}` |

   `ALLOWED_HOSTS` and CSRF trust are filled in automatically from `RAILWAY_PUBLIC_DOMAIN`. For a custom domain, set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
4. The first deploy migrates automatically. For sample data, run in the service **shell**: `python manage.py seed_demo` (and `seed_nosolowebs`).

### Known trade-offs

- **Avatars**: Railway's filesystem is ephemeral, so uploads don't survive a redeploy. Documented follow-up: S3 via `django-storages`.
- **No workers/email**: notifications and chat are fully in-app by design — this is a free-tier deployment, not a cut corner.

## Testing

```bash
python manage.py test
```

94 tests, covering tenant isolation, permissions, and core view/model behavior.

## About the author

Built by **Francisco Naranjo** — backend-leaning full-stack developer (Django/Python), currently open to opportunities.

- Portfolio: [francisconaranjonrvz.es](https://francisconaranjonrvz.es/)
- LinkedIn: [in/francisco-naranjo-narváez](https://www.linkedin.com/in/francisco-naranjo-narv%C3%A1ez-16231019b/)
- Email: [fconaranjonrvz@gmail.com](mailto:fconaranjonrvz@gmail.com)

## License

MIT — see [LICENSE](LICENSE).
