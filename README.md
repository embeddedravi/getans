# Ad Platform

A self-hosted ad server and campaign management platform. Publishers embed a
lightweight JavaScript snippet on their pages, ads are selected and delivered
in real time over Socket.IO, and advertisers/admins manage campaigns,
creatives, publishers, and analytics through a REST API plus a choice of two
dashboard frontends.

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [How ad delivery works](#how-ad-delivery-works)
- [Data model](#data-model)
- [Getting started](#getting-started)
  - [Quickstart with Docker](#quickstart-with-docker)
  - [Running the backend locally](#running-the-backend-locally)
  - [Running a dashboard locally](#running-a-dashboard-locally)
  - [Seeding a demo user](#seeding-a-demo-user)
- [Configuration](#configuration)
- [Embedding on a publisher site](#embedding-on-a-publisher-site)
- [API reference (summary)](#api-reference-summary)
- [Real-time events](#real-time-events)
- [Authentication & authorization](#authentication--authorization)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Project status](#project-status)

---

## Overview

This project has three main audiences:

- **Publishers** — website owners who embed an ad slot and receive served
  creatives in real time.
- **Advertisers** — create campaigns, set targeting rules and budgets, and
  upload creatives to run against those campaigns.
- **Admins** — manage publishers, ad units, and have visibility across all
  advertisers' campaigns and analytics.

Ad selection, budget enforcement, and event tracking all happen server-side,
with Redis used as a fast-path cache/counter and Postgres (or MySQL, see
[Configuration](#configuration)) as the durable store.

## Architecture

```
                        ┌──────────────────────┐
   Publisher's page ───▶│  publisher-snippet/   │
   (loader.js)          │  Socket.IO client     │
                        └───────────┬──────────┘
                                    │ /delivery namespace
                                    ▼
                        ┌──────────────────────┐
                        │   backend/ (FastAPI   │
                        │   + python-socketio)  │
                        │                       │
                        │  REST API ─────────┐  │
                        │  /delivery ns      │  │
                        │  /dashboard ns     │  │
                        └───────┬────────────┼──┘
                                │            │
                   ┌────────────┘            └───────────┐
                   ▼                                      ▼
           ┌───────────────┐                      ┌───────────────┐
           │   Postgres/    │                      │     Redis      │
           │   MySQL (data) │                      │ (budget cache, │
           │                │                      │  pub/sub relay)│
           └───────────────┘                      └───────────────┘

                                    ▲
                     REST calls     │
        ┌───────────────────────────┴───────────────────────────┐
        │                                                        │
┌───────────────┐                                      ┌──────────────────┐
│  dashboard/    │  React + Vite + Tailwind/DaisyUI      │ dashboard-flask/  │
│  (SPA)         │  talks directly to the REST API and   │  Server-rendered  │
│                │  the /dashboard Socket.IO namespace   │  Flask app that   │
│                │  for live metrics                     │  proxies all API  │
└───────────────┘                                      │  calls to backend │
                                                          └──────────────────┘
```

Two dashboard implementations are included — they are alternatives, not
dependent on one another. Pick whichever fits your stack, or use both during
evaluation.

## Project structure

```
.
├── backend/                 FastAPI + Socket.IO server
│   ├── app/
│   │   ├── api/             REST routers (auth, campaigns, creatives, publishers, analytics)
│   │   ├── core/            Security (JWT/bcrypt) and Redis client
│   │   ├── db/              SQLAlchemy base + async session factory
│   │   ├── models/          SQLAlchemy ORM models
│   │   ├── schemas/         Pydantic request/response schemas
│   │   ├── services/        Ad selection, budget tracking, publisher auth
│   │   ├── sockets/         Socket.IO namespaces (/delivery, /dashboard)
│   │   ├── config.py        Settings (env-driven)
│   │   ├── deps.py          FastAPI dependencies (DB session, auth)
│   │   └── main.py          App entrypoint / ASGI mount
│   ├── alembic/              DB migrations
│   ├── tests/                 Pytest suite (async, SQLite + fakeredis)
│   ├── create_demo_user.py    CLI script to seed a demo admin user
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── publisher-snippet/
│   └── src/loader.js         Embeddable JS loader for publisher sites
│
├── dashboard/                React SPA dashboard
│   ├── src/
│   │   ├── pages/            Analytics, Campaigns, Publishers, Login
│   │   ├── components/       Layout, Sidebar, TopBar
│   │   └── lib/               REST client (api.ts) + Socket.IO client (socket.ts)
│   └── vite.config.ts
│
├── dashboard-flask/           Server-rendered Flask dashboard (alternative UI)
│   ├── app.py                 Routes + API proxy to the backend
│   ├── templates/              Jinja2 templates (Tailwind + DaisyUI)
│   └── static/css/
│
├── docker-compose.yml         Postgres + Redis + backend
└── README.md
```

## How ad delivery works

1. A publisher's page loads `loader.js`, which connects once to the
   `/delivery` Socket.IO namespace and, for every element with
   `[data-ad-unit-id]`, emits a `request_ad` event containing the ad unit ID,
   the publisher's API key, and optional page context (country, device type,
   keywords).
2. The server authenticates the publisher's API key
   (`app/services/publisher_auth.py`, cached in Redis for 60s).
3. `app/services/ad_selector.py` selects the best eligible campaign:
   - Filters to campaigns that are **active**, within their **date window**,
     and have a creative matching the ad unit's **dimensions**.
   - Filters further by **targeting rules** (country / device type /
     keywords) against the request context.
   - Filters out campaigns that have **exhausted their daily budget** (a
     fast Redis counter, not a Postgres query, so this check doesn't add
     latency to every ad request).
   - Ranks the remainder by **priority**, breaking ties with weighted random
     selection so one campaign doesn't always win.
4. The winning creative is emitted back as `serve_ad`; if nothing is
   eligible, `no_fill` is emitted with a reason.
5. The loader renders the creative and emits `impression` immediately, and
   `click` when the ad is clicked.
6. `app/services/budget_tracker.py` records every impression/click durably
   in Postgres, increments the Redis spend counter used by the selector, and
   publishes a message on a Redis pub/sub channel.
7. The `/dashboard` Socket.IO namespace subscribes to that channel and
   relays `metric_update` events to any connected dashboard clients, so
   analytics update live without polling.

## Data model

| Table         | Purpose                                                        |
|---------------|-----------------------------------------------------------------|
| `publishers`  | A site running the ad snippet; owns an API key and ad units    |
| `ad_units`    | A named slot on a publisher's page with fixed width/height     |
| `advertisers` | An advertiser account; owns campaigns                          |
| `campaigns`   | Active window, priority, daily cap, targeting rules (JSON)     |
| `creatives`   | Assets belonging to a campaign, sized for a specific ad unit   |
| `events`      | Impression/click log, used for analytics and budget accounting |
| `users`       | Dashboard logins — `admin`, `advertiser`, or `publisher` role  |

Schema and relationships are defined in `backend/app/models/` and the initial
migration lives at `backend/alembic/versions/0001_initial.py`.

## Getting started

### Quickstart with Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Then apply migrations:

```bash
docker compose exec backend alembic upgrade head
```

- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/health

`docker-compose.yml` starts Postgres, Redis, and the backend. The dashboards
are not containerized yet — run them locally against the backend as
described below.

### Running the backend locally

Requires Python 3.11+.

```bash
cd backend
python -m venv zenv
zenv\Scripts\activate        # Windows
# source zenv/bin/activate   # macOS/Linux

pip install -e ".[dev]"
# or: pip install -r requirements.txt

cp .env.example .env         # edit values as needed
alembic upgrade head
uvicorn app.main:asgi_app --reload
```

The backend listens on `http://localhost:8000` by default. The combined ASGI
app mounts Socket.IO at `/socket.io/*` and everything else goes to FastAPI.

> **Note on bcrypt:** if you hit
> `ValueError: password cannot be longer than 72 bytes`, this is a known
> `passlib` + `bcrypt` version incompatibility, not an actual password-length
> issue. Pin `bcrypt<4.1` (already declared in `pyproject.toml`; add it to
> `requirements.txt` too if installing that way):
> ```bash
> pip install "bcrypt<4.1"
> ```

### Running a dashboard locally

**React SPA (`dashboard/`)**

```bash
cd dashboard
npm install
npm run dev
```

Runs on `http://localhost:5173` with `/api` and `/socket.io` proxied to the
backend (see `vite.config.ts`).

**Flask dashboard (`dashboard-flask/`)**

```bash
cd dashboard-flask
pip install -r requirements.txt
npm install
npm run build:css      # or: npm run watch:css
cp .env.example .env   # set API_BASE_URL and FLASK_SECRET_KEY
py app.py
```

Runs on `http://localhost:5000`. All API calls are proxied server-side to
the FastAPI backend.

### Seeding a demo user

From the `backend/` directory, with the virtual environment active and the
database migrated:

```bash
py create_demo_user.py
# or with custom credentials:
py create_demo_user.py --email admin@demo.com --password secret123 --role admin
```

`--role` accepts `admin`, `advertiser`, or `publisher`. Log in at whichever
dashboard you're running (`/login`).

## Configuration

Backend settings are loaded from environment variables (prefixed
`ADPLATFORM_`) or a `.env` file in `backend/`, via `app/config.py`. See
`backend/.env.example`:

| Variable                     | Purpose                                            | Default (dev only — override in production) |
|-------------------------------|-----------------------------------------------------|-----------------------------------------------|
| `ADPLATFORM_DATABASE_URL`     | SQLAlchemy async DB URL                              | See `.env.example`                           |
| `ADPLATFORM_JWT_SECRET`       | Secret used to sign dashboard JWTs                   | **Must be changed for any real deployment**  |
| `ADPLATFORM_CORS_ORIGINS`     | Allowed origins for the REST API                     | `["http://localhost:5173"]`                  |

The Flask dashboard has its own `.env` (`dashboard-flask/.env.example`):

| Variable             | Purpose                                  |
|----------------------|-------------------------------------------|
| `FLASK_SECRET_KEY`   | Session signing secret                    |
| `API_BASE_URL`       | Base URL of the backend REST API          |

**Security note:** the values shipped as defaults in `.env.example` files and
in `config.py` are placeholders for local development only. Always set real,
unique secrets and credentials via environment variables before deploying,
and never commit `.env` files (already covered by `.gitignore`).

## Embedding on a publisher site

```html
<div data-ad-unit-id="123"></div>
<script src="http://localhost:8000/static/loader.js"
        data-api-key="PUBLISHER_API_KEY"
        data-server="http://localhost:8000"></script>
```

- `data-ad-unit-id` on any element tells the loader to request and render an
  ad into that element.
- `data-api-key` is the publisher's API key, issued when the publisher is
  created (see `POST /api/publishers`) and visible in both dashboards.
- Serve `publisher-snippet/src/loader.js` as a static file, or bundle/minify
  it into your own build pipeline.

## API reference (summary)

All REST endpoints are prefixed `/api` and documented interactively at
`/docs` (Swagger) once the backend is running. Highlights:

| Method & path                         | Auth               | Description                          |
|----------------------------------------|--------------------|----------------------------------------|
| `POST /api/auth/login`                 | —                  | Exchange email/password for a JWT     |
| `GET  /api/auth/me`                    | Bearer token       | Current user info                     |
| `GET/POST /api/campaigns`              | admin, advertiser  | List / create campaigns (advertiser-scoped) |
| `GET/PATCH/DELETE /api/campaigns/{id}` | admin, advertiser  | Manage a single campaign              |
| `POST /api/creatives`                  | admin, advertiser  | Attach a creative to a campaign       |
| `GET /api/creatives/by-campaign/{id}`  | —                  | List creatives for a campaign         |
| `POST /api/publishers`                 | admin              | Create a publisher (issues API key)   |
| `GET /api/publishers`                  | —                  | List publishers                       |
| `POST/GET /api/publishers/{id}/ad-units` | —                | Manage a publisher's ad slots         |
| `GET /api/analytics/campaigns`         | admin, advertiser  | Impressions/clicks/CTR over a date range |

Advertiser-role users are always scoped to their own `advertiser_id` —
attempting to read or write another advertiser's campaigns returns `403`.

## Real-time events

**`/delivery` namespace** (publisher-facing, via `loader.js`)

| Direction        | Event         | Payload                                                        |
|-------------------|---------------|------------------------------------------------------------------|
| client → server   | `request_ad`  | `{ ad_unit_id, api_key, context? }`                               |
| server → client   | `serve_ad`    | `{ campaign_id, creative_id, asset_url, click_url, width, height }` |
| server → client   | `no_fill`     | `{ reason }`                                                      |
| client → server   | `impression`  | `{ ad_unit_id, creative_id }`                                     |
| client → server   | `click`       | `{ ad_unit_id, creative_id }`                                     |

**`/dashboard` namespace** (dashboard-facing)

| Direction        | Event            | Payload                                                  |
|-------------------|------------------|-------------------------------------------------------------|
| server → client   | `metric_update`  | `{ type, campaign_id, ad_unit_id, timestamp }`               |

Dashboard connections currently accept any client (see the `TODO` in
`app/sockets/dashboard_ns.py`) — before exposing this beyond local
development, add JWT authentication and scope clients to a room per
publisher/advertiser account.

## Authentication & authorization

- Dashboard users authenticate with email/password (`bcrypt` via `passlib`)
  and receive a JWT (`PyJWT`, HS256) valid for 12 hours by default
  (`jwt_expires_minutes` in `config.py`).
- Roles are `admin`, `advertiser`, and `publisher`. `require_role(...)` in
  `app/deps.py` gates individual endpoints.
- Advertiser-scoped endpoints additionally filter/validate against
  `user.advertiser_id` so advertisers can only see and modify their own data.
- Publisher-facing ad delivery uses a separate mechanism: a per-publisher API
  key (`app/services/publisher_auth.py`), not a JWT, cached in Redis.

## Testing

```bash
cd backend
pip install -e ".[dev]"
pytest
```

The test suite (`backend/tests/`) uses an in-memory SQLite database and
`fakeredis` in place of the real services, so it runs without Docker or any
external dependencies. Coverage includes:

- `test_ad_selector.py` — targeting, budget caps, priority ranking, dimension matching
- `test_auth_api.py` — login, token issuance, `/auth/me`
- `test_campaigns_api.py` — CRUD, advertiser scoping, validation (e.g. `end_date` after `start_date`)

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValueError: password cannot be longer than 72 bytes` | `passlib` + `bcrypt` ≥ 4.1 incompatibility | `pip install "bcrypt<4.1"` |
| `sqlalchemy.exc.NoReferencedTableError: ... could not find table 'publishers'` | A script only imports `app.models.user`, so related model tables were never registered on `Base.metadata` | Import all models (see `alembic/env.py` for the pattern) before touching the ORM |
| `redis.exceptions.ConnectionError: ... refused the network connection` | No Redis server running on `localhost:6379` | Start Redis: `docker run -d -p 6379:6379 redis:7`, or `docker compose up`, or run one locally/in WSL |
| Ads never render, `no_fill` always fires | No active campaign matches the ad unit's dimensions, targeting, or budget | Check campaign `is_active`, `start_date`/`end_date`, creative dimensions match the ad unit, and daily cap/spend in Redis |
| Dashboard shows `Disconnected` and no live metrics | `/dashboard` Socket.IO namespace not reachable, or backend not running the pub/sub relay task | Confirm backend started (`start_dashboard_relay` runs on FastAPI startup) and Redis is reachable |

## Project status

- [x] Data model + migrations
- [x] Ad selection (targeting + budget + priority)
- [x] Real-time delivery over Socket.IO
- [x] Campaign/creative/publisher REST CRUD + JWT auth
- [x] Event tracking + real-time budget decrement
- [x] Live dashboard metrics relay (Socket.IO + Redis pub/sub)
- [x] Dashboard frontend (React SPA + Flask alternative)
- [x] Backend test suite
- [ ] Dashboard authentication for the `/dashboard` Socket.IO namespace
- [ ] Production-hardened secrets management (no hardcoded defaults)
- [ ] Dashboard test coverage
