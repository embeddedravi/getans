# Ad Platform

A self-hosted ad server and campaign management platform (INR-only, India-first). Publishers embed a lightweight JavaScript snippet, ads are selected and delivered in real time over Socket.IO, and advertisers, publishers, staff, and admins manage everything through a REST API plus a choice of two dashboard frontends.

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [How ad delivery works](#how-ad-delivery-works)
- [Data model](#data-model)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Embedding on a publisher site](#embedding-on-a-publisher-site)
- [API reference (summary)](#api-reference-summary)
- [Real-time events](#real-time-events)
- [Authentication & authorization](#authentication--authorization)
- [Payments: wallets and payouts](#payments-wallets-and-payouts)
- [Moderation and approvals](#moderation-and-approvals)
- [Dashboard coverage](#dashboard-coverage)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Known gaps](#known-gaps)

---

## Overview

Four account roles use the platform:

| Role | What they do |
|---|---|
| **Publisher** | Registers a site, creates ad slots, embeds the snippet, tracks unpaid earnings. |
| **Advertiser** | Creates campaigns (targeting, bidding, budgets), uploads creatives, tops up an INR wallet via Razorpay. |
| **Staff** | Reviews pending publishers, advertisers, and ad units. |
| **Admin** | Everything staff can do, plus user management, creative review, payouts, advertiser payment history, ad slot activation, and a live event feed. |

Ad selection, budget enforcement, and event tracking happen server-side. Daily-cap spend tracking uses a fast in-process counter (`_spend_cache` in `app/services/ad_selector.py`); durable event records are written to MySQL.

## Architecture

![System Architecture](architectural_diagram.jpg)

- **Backend:** FastAPI + python-socketio on one ASGI app (`app.main:asgi_app`), SQLAlchemy 2 async, **MySQL 8** via `aiomysql`.
- **Dashboards:** two independent alternatives, a React SPA (`dashboard/`) and a server-rendered Flask app (`dashboard-flask/`). Both talk to the same REST API.
- **Publisher snippet:** `publisher-snippet/src/loader.js`, which connects to the `/delivery` Socket.IO namespace.
- There is no Redis or message broker; live metrics are relayed in-process.

## Project structure

```
.
├── backend/                     FastAPI + Socket.IO server
│   ├── app/
│   │   ├── api/                  Routers: auth, otp, campaigns, creatives, publishers,
│   │   │                         analytics, admin, payouts, advertiser_payments
│   │   ├── core/                 security.py (JWT/bcrypt), phone.py (Indian mobile normalization)
│   │   ├── db/                   Declarative base + async session factory
│   │   ├── models/               ORM models (incl. otp, payment, ad_report)
│   │   ├── schemas/              Pydantic schemas
│   │   ├── services/             ad_selector, budget_tracker, publisher_auth, otp, sms
│   │   ├── sockets/              /delivery and /dashboard namespaces
│   │   ├── config.py             Env-driven settings with production guards
│   │   ├── deps.py               DB session, current user, require_role
│   │   └── main.py               ASGI entrypoint
│   ├── alembic/                  Migrations
│   ├── tests/                    Pytest suite (async, in-memory SQLite)
│   ├── create_demo_user.py       Seed a user from the CLI
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── publisher-snippet/src/loader.js    Embeddable ad loader
│
├── dashboard/                   React SPA (Vite, Tailwind + DaisyUI, Vitest)
│   └── src/{pages,components,lib,tests}
│
├── dashboard-flask/             Flask dashboard (Jinja2, Tailwind + DaisyUI)
│   ├── app.py, verify_routes.py
│   ├── templates/
│   └── static/css/
│
├── docker-compose.yml           MySQL 8.4 + backend
└── README.md
```

## How ad delivery works

1. A publisher page loads `loader.js`, which connects to the `/delivery` namespace and, for every `[data-ad-unit-id]` element, emits `request_ad` with the ad unit ID, the publisher's API key, and page context (device type, keywords from `<meta name="keywords">`).
2. The server authenticates the API key (`publisher_auth.py`). The publisher must be `is_active` and in `active` status.
3. `ad_selector.py` first checks the ad unit: it must exist, be `is_active`, have status `approved`, and belong to an active publisher. Then it picks a campaign:
   - Campaign `is_active`, status `active` or `scheduled`, inside its date window (end date optional).
   - Advertiser account status `active`.
   - Has an **active, approved** creative matching the slot's exact width and height.
   - Passes **targeting rules** (countries, device types, keywords).
   - `bid_amount >= reserve_price` and daily cap not exhausted.
   - Highest **priority** tier wins; ties are broken randomly.
4. The winner is emitted as `serve_ad`; otherwise `no_fill` with a reason (`missing_params`, `unauthorized`, or the selector's message).
5. The loader renders the creative, emits `impression` immediately and `click` on click, and adds a **report** control (⚑) so visitors can flag the ad.
6. `budget_tracker.py` records each event with a fixed per-event cost, **deduplicated per visitor, ad unit, event type, and UTC day** (`dedupe_key`), updates the in-memory spend counter, and pushes `metric_update` and `live_event` messages to dashboards.

## Data model

| Table | Purpose | Notable fields |
|---|---|---|
| `users` | Dashboard logins | `mobile` (+91XXXXXXXXXX, unique), optional `email`, `role` (admin/staff/publisher/advertiser), `is_verified`, `is_superuser`, `publisher_id`/`advertiser_id` (check constraint enforces role↔tenant) |
| `otp_codes` | SMS one-time codes | HMAC `code_hash`, `expires_at`, `attempts`, `consumed_at` |
| `publishers` | Site running the snippet | `status` (pending_approval/active/suspended/rejected), `api_key`, `payout_email`, `revenue_share_percentage`, `unpaid_earnings`, `rejection_reason` |
| `ad_units` | A slot with fixed size | `status` (pending_review/approved/rejected), `is_active`, `reserve_price`, `format_type`, `report_review_round` |
| `advertisers` | Advertiser account | `status` (incl. pending_verification), `currency` (INR only), `balance`, `credit_limit`, `rejection_reason` |
| `campaigns` | Delivery config | `status`, `bidding_strategy` (cpm/cpc/cpa), `bid_amount`, `daily_cap`, `total_budget`, `spent_amount`, optional `end_date`, `targeting_rules` (JSON) |
| `creatives` | Ad assets | `review_status`, `rejection_reason`, `is_active`, `weight`, size |
| `events` | Impressions/clicks/conversions | `cost`, `is_valid`, `country_code`, `dedupe_key` (unique), `event_id` (unique) |
| `ad_reports` | Visitor reports of an ad | one per visitor per ad unit per review round |
| `advertiser_topups` | Razorpay wallet ledger | `order_id`, `payment_id`, `amount`, `status` (created/paid) |
| `payouts` | Publisher payouts | `status` (pending/processing/paid/failed/cancelled), `reference`, snapshot of `payout_email` |

Migrations live in `backend/alembic/versions/`. See [Troubleshooting](#troubleshooting) about the current branch in the migration history.

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+ (dashboards)
- MySQL 8 (or Docker)
- A Razorpay account (test keys are fine) if you want wallet top-ups

### Quickstart with Docker

Docker Compose needs MySQL passwords in a root-level `.env`, and the backend reads `backend/.env`:

```bash
# ./.env  (used by docker-compose.yml)
MYSQL_PASSWORD=choose-a-strong-password
MYSQL_ROOT_PASSWORD=choose-another-strong-password

cp backend/.env.example backend/.env
# edit backend/.env: set a real ADPLATFORM_JWT_SECRET (see Configuration)
# and ADPLATFORM_ENVIRONMENT=development for local use

docker compose up --build
docker compose exec backend alembic upgrade heads
```

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The compose file overrides `ADPLATFORM_DATABASE_URL` so both containers share one password. Dashboards are not containerized.

### Running the backend locally

```bash
cd backend
python -m venv zenv
source zenv/bin/activate        # Windows: zenv\Scripts\activate

pip install -e ".[dev]"
cp .env.example .env            # edit values (see Configuration)
alembic upgrade heads
uvicorn app.main:asgi_app --reload
```

Listens on `http://localhost:8000`. Socket.IO is mounted at `/socket.io/*`; everything else is FastAPI.

> **bcrypt:** `passlib` needs `bcrypt<4.1` (already pinned). If you see `password cannot be longer than 72 bytes`, run `pip install "bcrypt<4.1"`.

### Running a dashboard

**React SPA**

```bash
cd dashboard
npm install
npm run dev          # http://localhost:5173, proxies /api and /socket.io to :8000
```

**Flask dashboard**

```bash
cd dashboard-flask
pip install -r requirements.txt
npm install
npm run build:css
cp .env.example .env
python app.py        # http://localhost:5000
```

Flask notes:

- `FLASK_SECRET_KEY` must be at least 32 random characters (the app refuses to start otherwise).
- Session cookies are `Secure` by default. For plain-HTTP local development set `FLASK_INSECURE_COOKIES=1`.
- `FLASK_DEBUG=1` enables debug mode.

### Seeding a user

```bash
cd backend
python create_demo_user.py                          # admin, mobile 9876543210, random password printed
python create_demo_user.py --mobile 9811122333 --role staff --password 'S3cretpass!'
```

Options: `--mobile`, `--email`, `--password` (omit to generate), `--role` (`admin`, `staff`, `advertiser`, `publisher`; default `admin`), `--allow-production`. The script refuses to run when `ADPLATFORM_ENVIRONMENT=production` unless `--allow-production` is passed. Note that `advertiser` and `publisher` users need a tenant ID, so create those through signup instead.

## Configuration

Settings load from environment variables prefixed `ADPLATFORM_`, a `.env` file, or Docker/Kubernetes secret files in `/run/secrets` (for example `/run/secrets/adplatform_jwt_secret`).

Secrets have **no defaults**, and the app refuses to start with a missing or weak secret.

| Variable | Purpose | Default |
|---|---|---|
| `ADPLATFORM_ENVIRONMENT` | `development`, `test`, or `production` | `production` |
| `ADPLATFORM_DATABASE_URL` | Must be `mysql+aiomysql://user:pass@host:3306/db` | required |
| `ADPLATFORM_JWT_SECRET` | ≥ 32 random chars, not a placeholder | required |
| `ADPLATFORM_JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ADPLATFORM_JWT_EXPIRES_MINUTES` | Token lifetime | `720` |
| `ADPLATFORM_CORS_ORIGINS` | JSON list of allowed REST origins | `["http://localhost:5173"]` |
| `ADPLATFORM_SOCKETIO_CORS_ALLOWED_ORIGINS` | Socket.IO CORS (publisher sites vary; auth is by API key) | `*` |
| `ADPLATFORM_OTP_LENGTH` / `_TTL_SECONDS` / `_MAX_ATTEMPTS` | OTP format, expiry (300 s), attempts (5) | `6` / `300` / `5` |
| `ADPLATFORM_OTP_RESEND_COOLDOWN_SECONDS` / `_MAX_PER_HOUR` | OTP rate limits | `60` / `5` |
| `ADPLATFORM_SMS_BACKEND` | `console` logs the OTP (dev only); anything else must be implemented in `app/services/sms.py` | `console` |
| `ADPLATFORM_REQUIRE_VERIFIED_MOBILE` | Block login and live sockets until the mobile is verified | `false` |
| `ADPLATFORM_ALLOW_SELF_SIGNUP` | Enable `/api/auth/signup` | `true` |
| `ADPLATFORM_RAZORPAY_KEY_ID` / `_KEY_SECRET` | Required for wallet top-ups | unset |

**Production guards:** with `ENVIRONMENT=production` the app refuses to start if `SMS_BACKEND=console`, if `CORS_ORIGINS` contains `*`, or if the database password is empty or a known weak value. The shipped `.env.example` has a placeholder JWT secret that will fail validation, and it does not set `ENVIRONMENT`, so add `ADPLATFORM_ENVIRONMENT=development` for local work.

**SMS:** implement a real provider (MSG91, Twilio, etc.) in `send_sms()` before going to production.

**Flask dashboard** (`dashboard-flask/.env`): `FLASK_SECRET_KEY`, `API_BASE_URL` (default `http://localhost:8000/api`), plus the optional `FLASK_INSECURE_COOKIES` and `FLASK_DEBUG` flags above.

## Embedding on a publisher site

```html
<div data-ad-unit-id="123"></div>
<script src="https://cdn.socket.io/4.8.1/socket.io.min.js"></script>
<script src="https://your-cdn.example.com/loader.js"
        data-api-key="PUBLISHER_API_KEY"
        data-server="https://your-ad-server.example.com"></script>
```

- The loader expects `window.io` to exist, so **load the Socket.IO client first** (the loader does not inject it).
- `loader.js` is not served by the backend. Host `publisher-snippet/src/loader.js` yourself or bundle/minify it.
- `data-api-key` comes from the publisher record (visible in both dashboards).
- A slot only serves once the publisher is `active` **and** the ad unit is `approved` and active. New signups start as pending.
- Visitors can click ⚑ on a served ad to report it. At 3 distinct visitor reports in one review round, the ad unit moves to `pending_review` and stops serving until an admin or staff member reviews it.

## API reference (summary)

All REST endpoints are under `/api` and documented at `/docs`.

| Area | Endpoints | Roles |
|---|---|---|
| Auth | `POST /auth/login`, `GET /auth/me`, `POST /auth/signup`, `POST /auth/register`, `POST /auth/forgot-password/reset` | login/signup/reset public; register: admin |
| OTP | `POST /auth/otp/request`, `POST /auth/otp/verify` | public |
| Campaigns | `GET/POST /campaigns`, `GET/PATCH/DELETE /campaigns/{id}` | admin, advertiser (scoped) |
| Creatives | `POST /creatives`, `GET /creatives/by-campaign/{id}`, `PATCH/DELETE /creatives/{id}`, `PATCH /creatives/{id}/review` | admin, advertiser; review: admin |
| Publishers | `GET/POST /publishers`, `GET /publishers/{id}`, `GET/POST /publishers/{id}/ad-units` | admin, publisher (scoped); create publisher: admin |
| Analytics | `GET /analytics/campaigns?start=&end=` | admin, advertiser |
| Admin | `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/advertisers`, `GET /admin/approvals/pending`, `PATCH /admin/{publishers\|advertisers\|ad-units}/{id}/review`, `PATCH /admin/ad-units/{id}/active`, `GET /admin/ad-units/{id}/reports`, `GET /admin/events/recent` | admin (some also staff) |
| Wallet | `GET /payments/wallet`, `POST /payments/orders`, `POST /payments/verify` | advertiser |
| Top-up ledger | `GET /payments/topups` | admin |
| Payouts | `POST/GET /payouts`, `GET/PATCH /payouts/{id}` | create/update: admin; list/get: admin, publisher (scoped) |
| Health | `GET /health` | public |

Key request rules:

- **Mobile numbers** are normalized to `+91XXXXXXXXXX`. Accepted inputs include `98765 43210`, `09876543210`, `919876543210`, and `+91…`. Numbers must start with 6–9.
- **Signup** needs `mobile`, `password` (8–72 chars), `role` (advertiser/publisher), `organization_name`. Publishers also need `site_url` and `payout_email`; advertisers need `billing_email` or `email`. New publishers and advertisers start pending approval.
- **Campaigns** need `advertiser_id`, `name`, `start_date`. `end_date` is optional and must be after `start_date`. `priority` is 1–100.
- **Creatives** start `pending` and must be approved before they can serve. Width and height must exactly match a slot.
- **Ad units** need `publisher_id` (matching the path), `slot_name`, `width`, `height`.

## Real-time events

**`/delivery`** (publisher snippet)

| Direction | Event | Payload |
|---|---|---|
| client → server | `request_ad` | `{ ad_unit_id, api_key, context? }` |
| server → client | `serve_ad` | `{ campaign_id, creative_id, asset_url, click_url, width, height }` |
| server → client | `no_fill` | `{ reason }` |
| client → server | `impression` / `click` | `{ ad_unit_id, creative_id, visitor_id, event_id }` |
| client → server | `report_ad` (ack) | `{ api_key, ad_unit_id, creative_id, visitor_id, reason }` |

Report reasons: `misleading`, `adult_content`, `inappropriate`, `scam`, `other`.

**`/dashboard`** (dashboards)

| Direction | Event | Payload | Rooms |
|---|---|---|---|
| server → client | `metric_update` | `{ type, campaign_id, ad_unit_id, timestamp }` | admin + owning advertiser + owning publisher |
| server → client | `live_event` | full event row with campaign and slot names, cost, country | admin only |

The handshake needs a dashboard JWT: `io("/dashboard", { auth: { token } })`. Invalid, expired, or deactivated-user tokens are refused with `unauthorized`. The role comes from the database, not the token. Sockets close when the token expires. Staff users have no room and cannot connect.

The Flask live-events page polls `/proxy/live-events` every 2 seconds instead of using sockets.

## Authentication & authorization

- **Login** is by mobile number and password (bcrypt). Email is optional and only a secondary identifier.
- **JWT** (HS256, 12 h by default) carries `role`, `publisher_id`, `advertiser_id` for convenience, but every request re-loads the user and enforces `is_active`.
- **Mobile verification:** SMS OTP (HMAC-hashed, 5-minute expiry, 5 attempts, 60 s resend cooldown, 5 codes/hour). `/auth/otp/request` returns the same response whether or not the number exists. Verifying marks the user `is_verified`. Set `REQUIRE_VERIFIED_MOBILE=true` to enforce it at login.
- **Password reset** uses the same OTP flow via `/auth/forgot-password/reset`.
- **Roles:** `require_role(...)` in `app/deps.py` gates endpoints. Advertiser and publisher users are scoped to their own tenant ID.
- **Admin safeguards:** superusers can't be edited, admins can't demote or deactivate themselves, and the last active admin can't be removed.
- **Publisher delivery** uses a separate per-publisher API key checked on each `request_ad`.

## Payments: wallets and payouts

**Advertiser wallet (Razorpay).** Active advertisers add ₹1 to ₹5,00,000 from the dashboard. The server creates a Razorpay order, then on checkout success verifies the signature, fetches the payment from Razorpay, captures it if only authorized, checks order ID, amount, and currency, and credits the wallet exactly once. No webhook is needed. Use test keys while developing.

**Publisher payouts.** Admins create payouts against a publisher's `unpaid_earnings`. Open payouts (pending or processing) reserve balance, so you can't over-allocate. Marking a payout `paid` decrements `unpaid_earnings`; `failed` requires a reason and frees the reserved balance. Terminal states are immutable.

## Moderation and approvals

- Publishers, advertisers, and ad units start pending. Admin or staff approve or reject (a reason is required to reject). Admins can also suspend and reactivate publishers and advertisers.
- Creatives are reviewed by admins only.
- Approving or rejecting an ad unit starts a new visitor-report round.

## Dashboard coverage

| Feature | React SPA | Flask |
|---|---|---|
| Login, signup, mobile verification, forgot password | ✔ | ✔ |
| Role-based navigation (admin / staff / publisher / advertiser) | ✔ | ✔ |
| Analytics (live counters + 7-day chart) | ✔ (role-specific overview) | ✔ |
| Campaigns: create, publish draft, pause/activate, delete | ✔ | ✔ (no publish button) |
| Creatives: add, toggle, review (admin), delete | ✔ (modal) | ✔ (page) |
| Publishers and ad slots | ✔ | ✔ |
| Approvals queue | ✔ | ✔ |
| Manage advertisers / publishers / ad slots / users (admin) | ✔ | ✔ |
| Visitor reports per ad slot | ✔ | ✘ |
| Live events feed (admin) | ✔ (sockets) | ✔ (polling) |
| Advertiser wallet top-up | ✔ (on overview) | ✔ (`/wallet`) |
| Admin view of advertiser top-ups | ✔ (`/payments`) | ✘ |
| Publisher payouts (admin) | ✔ (`/payouts`) | ✔ (`/payments`) |

Route names differ: in the React app `/payments` is advertiser top-ups and `/payouts` is publisher payouts; in Flask `/payments` is publisher payouts.

## Testing

**Backend** (no external services needed; in-memory SQLite):

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Covers ad selection, auth, signup, OTP, campaigns, payouts, and the dashboard socket namespace (auth, room scoping, expiry).

**React dashboard** (Vitest + Testing Library):

```bash
cd dashboard
npm test
npm run test:coverage
```

> The `dev` extra in `pyproject.toml` doesn't list `fakeredis`, which `egg-info` mentions from an older build. Redis is no longer used.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App exits at startup with a secret/production error | Weak or placeholder `JWT_SECRET`, `SMS_BACKEND=console`, `*` in CORS, or weak DB password under `ENVIRONMENT=production` | Set real values, or `ADPLATFORM_ENVIRONMENT=development` locally |
| `alembic upgrade head` reports multiple heads | `4b77b00f4152` and `a1b2c3d4e5f6` both descend from `9d4e1f2a3b44` | Run `alembic upgrade heads`, or create a merge revision with `alembic merge` |
| Docker build fails on `COPY alembic.ini` | `backend/alembic.ini` is git-ignored | Create it locally before building |
| Flask login works but session is lost on `http://localhost` | Secure cookies | Set `FLASK_INSECURE_COOKIES=1` for dev |
| Flask refuses to start | `FLASK_SECRET_KEY` shorter than 32 chars or contains "change" | Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| No OTP arrives | `SMS_BACKEND=console` | Read the code from the backend log, or implement a real provider |
| `403 Mobile number not verified` | `REQUIRE_VERIFIED_MOBILE=true` | Complete verification at `/verify` |
| Ads never render, `no_fill` always | Publisher not active, ad unit not approved/active, no approved creative of the exact size, targeting mismatch, `bid_amount < reserve_price`, or cap exhausted | Check each in turn; the `no_fill` reason is logged server-side |
| Ad slot suddenly stops serving | 3 visitor reports moved it to `pending_review` | Review the reports in the admin slots page |
| Loader logs "Socket.IO client did not initialize" | Socket.IO client script not loaded first | Add the client `<script>` before `loader.js` |
| Dashboard shows "Disconnected" | `/socket.io` not proxied or token rejected | Check `vite.config.ts` proxy and that the user is active (and verified if required) |
| `NoReferencedTableError` in a script | Only some models imported | Import `app.models` (it registers all models) |
| Wallet "Razorpay is not configured" (503) | Missing Razorpay keys | Set `ADPLATFORM_RAZORPAY_KEY_ID` and `_KEY_SECRET` |

## Known gaps

These are current behaviors worth knowing before relying on the platform for billing:

- **Event cost is fixed.** `budget_tracker.py` charges constant per-event amounts (impression ₹0.001, click ₹0.10, conversion ₹1.00) rather than the campaign's `bid_amount` and strategy.
- **Spend isn't persisted to balances.** Events update only the in-memory daily-cap counter. `campaigns.spent_amount`, advertiser `balance`, and publisher `unpaid_earnings` are not updated by event tracking, and the counter resets on restart and isn't shared between workers.
- **`total_budget` isn't enforced** during selection (only `daily_cap`).
- **`viewable_impression` events** are accepted by the schema but have no cost mapping and can't be recorded.
- **Payout payment methods** (`stripe`, `paypal`, `wire_transfer`) are labels only; no payout gateway is integrated.
- **`admin.py` defines `AdUnitActivation` and `set_ad_unit_active` twice**; harmless but worth cleaning up.
