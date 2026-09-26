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
  - [Prerequisites](#prerequisites)
  - [Quickstart with Docker](#quickstart-with-docker)
  - [Running the backend locally](#running-the-backend-locally)
  - [Running a dashboard locally](#running-a-dashboard-locally)
  - [Seeding a demo user](#seeding-a-demo-user)
- [Configuration](#configuration)
- [Embedding on a publisher site](#embedding-on-a-publisher-site)
- [API reference (summary)](#api-reference-summary)
- [Real-time events](#real-time-events)
- [Authentication & authorization](#authentication--authorization)
- [Dashboard coverage](#dashboard-coverage)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Project status](#project-status)

---

## Overview

This project has three main audiences:

- **Publishers** — website owners who embed an ad slot and receive served
  creatives in real time.
- **Advertisers** — create campaigns, set targeting rules, bidding, and
  budgets, and upload creatives to run against those campaigns.
- **Admins** — manage publishers, ad units, and have visibility across all
  advertisers' campaigns and analytics.

Ad selection, budget enforcement, and event tracking all happen server-side.
Daily-cap spend tracking uses a fast in-process counter (`_spend_cache` in
`app/services/ad_selector.py`) so it doesn't add latency to every ad
request; durable records (events, campaign `spent_amount`) are written to
the relational database.

## Architecture

![System Architecture](architectural_diagram.jpg)

Two dashboard implementations are included — they are alternatives, not
dependent on one another. Pick whichever fits your stack, or run both during
evaluation. Both currently cover publishers, ad units, campaigns, and
analytics; neither has a UI for the creatives API yet (see
[Dashboard coverage](#dashboard-coverage)).

> **Note on the database:** `app/config.py` defaults `database_url` to a
> local MySQL connection string and `backend/requirements.txt` lists
> `aiomysql`, while `backend/pyproject.toml` lists `asyncpg` and
> `docker-compose.yml` provisions Postgres. Either async driver works with
> the SQLAlchemy models as written — just make sure `ADPLATFORM_DATABASE_URL`
> and the installed driver package agree with whichever database you
> actually run. There is currently no Redis dependency in the code path
> (dashboard metrics are relayed in-process via `emit_metric_update`), even
> though `redis` appears in some dependency lists as a holdover.

## Project structure

```
.
├── backend/                    FastAPI + Socket.IO server
│   ├── app/
│   │   ├── api/                 REST routers (auth, campaigns, creatives, publishers, analytics)
│   │   ├── core/                 Security (JWT/bcrypt) and Redis client stub
│   │   ├── db/                    SQLAlchemy base + async session factory
│   │   ├── models/                SQLAlchemy ORM models
│   │   ├── schemas/                Pydantic request/response schemas
│   │   ├── services/                Ad selection, budget tracking, publisher auth
│   │   ├── sockets/                  Socket.IO namespaces (/delivery, /dashboard)
│   │   ├── config.py                  Settings (env-driven)
│   │   ├── deps.py                    FastAPI dependencies (DB session, auth, role checks)
│   │   └── main.py                     App entrypoint / ASGI mount
│   ├── alembic/                  DB migrations (async-aware env.py)
│   ├── tests/                      Pytest suite (async, in-memory SQLite)
│   ├── create_demo_user.py           CLI script to seed a demo user
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── publisher-snippet/
│   └── src/loader.js            Embeddable JS loader for publisher sites
│
├── dashboard/                    React SPA dashboard
│   ├── src/
│   │   ├── pages/                 Analytics, Campaigns, Publishers, Login
│   │   ├── components/             Layout, Sidebar, TopBar
│   │   └── lib/                      REST client (api.ts) + Socket.IO client (socket.ts)
│   └── vite.config.ts
│
├── dashboard-flask/                Server-rendered Flask dashboard (alternative UI)
│   ├── app.py                        Routes + API proxy to the backend
│   ├── templates/                      Jinja2 templates (Tailwind + DaisyUI)
│   └── static/css/
│
├── docker-compose.yml               Postgres + backend
└── README.md
```

## How ad delivery works

1. A publisher's page loads `loader.js`, which connects once to the
   `/delivery` Socket.IO namespace and, for every element with
   `[data-ad-unit-id]`, emits a `request_ad` event containing the ad unit ID,
   the publisher's API key, and optional page context (country, device type,
   keywords parsed from a `<meta name="keywords">` tag).
2. The server authenticates the publisher's API key
   (`app/services/publisher_auth.py`), rejecting publishers that are
   inactive or not in `active` status.
3. `app/services/ad_selector.py` selects the best eligible campaign:
   - Filters to campaigns that are **active** (both `is_active` and
     `status` in `active`/`scheduled`), within their **date window** (an
     end date is optional — an open-ended campaign never expires), and have
     an **approved, active** creative matching the ad unit's **dimensions**.
   - Filters further by **targeting rules** (country / device type /
     keywords) against the request context.
   - Filters out campaigns whose **bid amount is below the ad unit's
     reserve price**, and campaigns that have **exhausted their daily
     budget** (a fast in-memory spend counter, not a database query on
     every request).
   - Ranks the remainder by **priority**, breaking ties with weighted random
     selection so one campaign doesn't always win.
4. The winning creative is emitted back as `serve_ad`; if nothing is
   eligible, `no_fill` is emitted with a reason (`missing_params`,
   `unauthorized`, or a message from `NoEligibleCampaignError`).
5. The loader renders the creative and emits `impression` immediately, and
   `click` when the ad is clicked.
6. `app/services/budget_tracker.py` records every impression/click durably
   (with a per-event `cost` based on the campaign's bidding strategy —
   CPM/CPC/CPA), increments the campaign's spend counter used by the
   selector, and updates `spent_amount`.
7. The `/dashboard` Socket.IO namespace relays `metric_update` events to any
   connected dashboard clients directly (same process, no pub/sub broker),
   so analytics update live without polling.

## Data model

| Table         | Purpose                                                        | Notable fields |
|---------------|-----------------------------------------------------------------|-----------------|
| `publishers`  | A site running the ad snippet; owns an API key and ad units    | `status` (pending_approval/active/suspended/rejected), `payout_email` (required), `revenue_share_percentage`, `unpaid_earnings`, `ads_txt_verified`, `domain`, `category`, auto-generated `api_key` |
| `ad_units`    | A named slot on a publisher's page with fixed width/height     | `format_type` (display/banner/native/video/interstitial), `reserve_price` (CPM floor), `is_active`, `allow_house_ads`, `settings` (JSON) |
| `advertisers` | An advertiser account; owns campaigns                          | `status`, `currency`, `balance`, `credit_limit`, `is_verified` |
| `campaigns`   | Delivery window, priority, bidding, budget, targeting rules     | `status` (draft/scheduled/active/paused/completed/exhausted/archived), `bidding_strategy` (cpm/cpc/cpa), `bid_amount`, `daily_cap`, `total_budget`, `spent_amount`, `end_date` (optional — omit for an open-ended campaign), `targeting_rules` (JSON: countries/device_types/keywords) |
| `creatives`   | Assets belonging to a campaign, sized for a specific ad unit   | `review_status` (pending/approved/rejected), `rejection_reason`, `is_active`, `impression_tracker_url`, `weight` |
| `events`      | Impression/click/conversion log, used for analytics and budget accounting | `cost`, `is_valid`, `country_code`, `user_ip`, `user_agent` |
| `users`       | Dashboard logins — `admin`, `advertiser`, or `publisher` role  | scoped via `publisher_id` / `advertiser_id`; a DB check constraint enforces role/tenant pairing |

Schema and relationships are defined in `backend/app/models/`; migrations
live under `backend/alembic/versions/` (`0001_initial` establishes the base
schema, `6f7a8f1e1745_...` adds the richer status/targeting/bidding columns
used by the current models).

## Getting started

### Prerequisites

- Python 3.11+
- Node.js (for either dashboard's build tooling)
- A relational database reachable via an async driver — Postgres
  (`asyncpg`) or MySQL (`aiomysql`)
- Docker + Docker Compose, if you want the quickstart path

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

`docker-compose.yml` starts Postgres and the backend. The dashboards are not
containerized — run them locally against the backend as described below.

### Running the backend locally

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
app (`app/main.py`) mounts Socket.IO at `/socket.io/*` and everything else
goes to FastAPI.

> **Note on bcrypt:** if you hit
> `ValueError: password cannot be longer than 72 bytes`, this is a known
> `passlib` + `bcrypt` version incompatibility, not an actual password-length
> issue. Pin `bcrypt<4.1` (already declared in `pyproject.toml` and
> `requirements.txt`):
> ```bash
> pip install "bcrypt<4.1"
> ```

> **Note on email validation:** `PublisherCreate.payout_email` and several
> other schemas use Pydantic's `EmailStr`, which requires the
> `email-validator` package. It's listed in `backend/requirements.txt`; if
> you installed via `pyproject.toml` and see an import error for it, run
> `pip install email-validator`.

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
the FastAPI backend via `requests`.

### Seeding a demo user

From the `backend/` directory, with the virtual environment active and the
database migrated:

```bash
py create_demo_user.py
# or with custom credentials:
py create_demo_user.py --email admin@demo.com --password secret123 --role admin
```

`--role` accepts `admin`, `advertiser`, or `publisher` (default role in the
script is `advertiser`). Log in at whichever dashboard you're running
(`/login`).

## Configuration

Backend settings are loaded from environment variables (prefixed
`ADPLATFORM_`) or a `.env` file in `backend/`, via `app/config.py`. See
`backend/.env.example`:

| Variable                     | Purpose                                            | Default (dev only — override in production) |
|-------------------------------|-----------------------------------------------------|-----------------------------------------------|
| `ADPLATFORM_DATABASE_URL`     | SQLAlchemy async DB URL                              | `mysql+aiomysql://root:password@localhost:3306/mydb` |
| `ADPLATFORM_JWT_SECRET`       | Secret used to sign dashboard JWTs                   | **Must be changed for any real deployment**  |
| `ADPLATFORM_JWT_ALGORITHM`    | JWT signing algorithm                                | `HS256`                                       |
| `ADPLATFORM_JWT_EXPIRES_MINUTES` | Token lifetime, in minutes                        | `720` (12 hours)                              |
| `ADPLATFORM_CORS_ORIGINS`     | Allowed origins for the REST API                     | `["http://localhost:5173"]`                  |
| `ADPLATFORM_SOCKETIO_ASYNC_MODE` | python-socketio async mode                        | `asgi`                                        |
| `ADPLATFORM_SOCKETIO_CORS_ALLOWED_ORIGINS` | CORS for Socket.IO connections (publisher sites vary; tighten via API-key auth instead) | `*` |

The Flask dashboard has its own `.env` (`dashboard-flask/.env.example`):

| Variable             | Purpose                                  |
|----------------------|-------------------------------------------|
| `FLASK_SECRET_KEY`   | Session signing secret                    |
| `API_BASE_URL`       | Base URL of the backend REST API          |

**Security note:** the values shipped as defaults in `.env.example` files
and in `config.py` are placeholders for local development only. Always set
real, unique secrets and credentials via environment variables before
deploying, and never commit `.env` files (already covered by `.gitignore`).

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
  created (`POST /api/publishers`) and visible in both dashboards.
- A publisher must be in `active` status (and `is_active`) for its ad units
  to serve; a newly created publisher starts in `pending_approval`.
- The loader lazily injects the official Socket.IO client script from
  `<data-server>/socket.io/socket.io.js` if `window.io` isn't already
  present.
- Serve `publisher-snippet/src/loader.js` as a static file, or bundle/minify
  it into your own build pipeline — it isn't wired into the FastAPI static
  file serving by default.

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
| `GET /api/creatives/by-campaign/{id}`  | admin, advertiser  | List creatives for a campaign         |
| `DELETE /api/creatives/{id}`           | admin, advertiser  | Delete a creative                     |
| `POST /api/publishers`                 | admin              | Create a publisher (issues API key)   |
| `GET /api/publishers`                  | admin, publisher   | List publishers (publisher-scoped for that role) |
| `GET /api/publishers/{id}`             | admin, publisher   | Get a single publisher                |
| `POST/GET /api/publishers/{id}/ad-units` | admin, publisher | Manage a publisher's ad slots         |
| `GET /api/analytics/campaigns`         | admin, advertiser  | Impressions/clicks/CTR over a date range |
| `GET /health`                          | —                  | Liveness check                        |

Advertiser-role users are always scoped to their own `advertiser_id` —
attempting to read or write another advertiser's campaigns returns `403`.
Publisher-role users are scoped to their own `publisher_id` for publisher
and ad-unit endpoints.

**Required fields to watch for:**

- `POST /api/publishers` requires `name`, `site_url`, **and `payout_email`**
  (a valid email address, no default) — omitting it returns `422`.
- `POST /api/campaigns` requires `advertiser_id`, `name`, and `start_date`.
  `bidding_strategy` (defaults `cpm`), `bid_amount` (defaults `1.0000`), and
  `priority` (defaults `1`, range `1`–`100`) can be left out and will use
  their defaults. `end_date`, `daily_cap`, and `total_budget` are all
  optional; when provided, `end_date` must be strictly after `start_date`
  (`400` otherwise).
- `POST /api/publishers/{id}/ad-units` requires `publisher_id`, `slot_name`,
  `width`, `height`. `format_type` defaults to `display` and
  `reserve_price` defaults to `0`.
- `POST /api/creatives` requires `campaign_id`, `asset_url`, `click_url`,
  `width`, `height`. `format` defaults to `image`; newly created creatives
  start with `review_status = pending` and must be approved before they can
  be selected for delivery.

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
  (`jwt_expires_minutes` in `config.py`), carrying `role`, `publisher_id`,
  and `advertiser_id` as extra claims.
- Roles are `admin`, `advertiser`, and `publisher`. `require_role(...)` in
  `app/deps.py` gates individual endpoints.
- Advertiser-scoped endpoints additionally filter/validate against
  `user.advertiser_id`, and publisher-scoped endpoints against
  `user.publisher_id`, so each account can only see and modify its own
  data.
- Publisher-facing ad delivery uses a separate mechanism: a per-publisher
  API key (`app/services/publisher_auth.py`), not a JWT, checked on every
  `request_ad` Socket.IO event.

## Dashboard coverage

Both `dashboard/` (React) and `dashboard-flask/` (server-rendered) currently
cover:

- Login / JWT session handling
- Live + historical analytics (impressions, clicks, CTR)
- Campaigns: list, create (with priority, bidding strategy, bid amount,
  daily cap, total budget, optional end date), toggle active/paused, delete
- Publishers: list, create (name, site URL, **payout email**, optional
  domain/category), view API key, status, revenue share, unpaid earnings
- Ad units: list, create (slot name, format, dimensions, reserve price)

**Not yet covered by either dashboard:** the creatives API
(`POST /api/creatives`, `GET /api/creatives/by-campaign/{id}`,
`DELETE /api/creatives/{id}`) — asset URL, click URL, format, dimensions,
and review status (`pending` / `approved` / `rejected`) currently have to be
managed directly against the REST API or via `/docs`. A campaign can't
serve until it has at least one **active, approved** creative matching an
ad unit's dimensions.

## Testing

```bash
cd backend
pip install -e ".[dev]"
pytest
```

The test suite (`backend/tests/`) uses an in-memory SQLite database
(`aiosqlite`) in place of the real database, so it runs without Docker or
any external dependencies. Coverage includes:

- `test_ad_selector.py` — targeting, budget caps, priority ranking, dimension matching
- `test_auth_api.py` — login, token issuance, `/auth/me`
- `test_campaigns_api.py` — CRUD, advertiser scoping, validation (e.g. `end_date` after `start_date`)

Fixtures in `backend/tests/conftest.py` override the app's `get_db`
dependency and monkeypatch the session factories used by
`publisher_auth` and `budget_tracker`, so tests never touch a real
database.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValueError: password cannot be longer than 72 bytes` | `passlib` + `bcrypt` ≥ 4.1 incompatibility | `pip install "bcrypt<4.1"` |
| `422 Unprocessable Entity` creating a publisher | `payout_email` missing from the request body | Include a valid `payout_email`; both dashboards send it by default |
| `sqlalchemy.exc.NoReferencedTableError: ... could not find table 'publishers'` | A script only imports `app.models.user`, so related model tables were never registered on `Base.metadata` | Import all models (see `app/models/__init__.py` or `alembic/env.py` for the pattern) before touching the ORM |
| Ads never render, `no_fill` always fires | No active campaign matches the ad unit's dimensions, targeting, budget, or reserve price | Check campaign `is_active`/`status`, `start_date`/`end_date`, that it has a creative with `is_active=true` and `review_status=approved` matching the ad unit's dimensions, that `bid_amount >= reserve_price`, and remaining daily/total budget |
| Dashboard shows `Disconnected` and no live metrics | `/dashboard` Socket.IO namespace not reachable | Confirm the backend is running and reachable at the configured server URL, and that `/socket.io` is proxied (see `vite.config.ts` for the React dashboard) |
| `401` right after logging in, on every subsequent request | Token not attached, or `ADPLATFORM_JWT_SECRET` changed between issuing and validating the token | Confirm `Authorization: Bearer <token>` is sent, and that the backend hasn't restarted with a new secret since login |
| Database driver import errors on startup | `ADPLATFORM_DATABASE_URL` scheme doesn't match the installed async driver | Use `asyncpg` for `postgresql+asyncpg://...` or `aiomysql` for `mysql+aiomysql://...`, and install the matching package |

## Project status

- [x] Data model + migrations
- [x] Ad selection (targeting + budget + reserve price + priority)
- [x] Real-time delivery over Socket.IO
- [x] Campaign/creative/publisher REST CRUD + JWT auth
- [x] Event tracking + real-time budget decrement
- [x] Live dashboard metrics relay (Socket.IO)
- [x] Dashboard frontend (React SPA + Flask alternative) for publishers, ad units, campaigns, analytics
- [x] Backend test suite
- [ ] Creatives management UI in either dashboard
- [ ] Dashboard authentication for the `/dashboard` Socket.IO namespace
- [ ] Production-hardened secrets management (no hardcoded defaults)
- [ ] Dashboard test coverage
- [ ] Reconcile database driver/dependency lists (`pyproject.toml` vs `requirements.txt` vs `docker-compose.yml`)