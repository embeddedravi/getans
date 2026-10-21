# GetANS

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

Ad selection, budget enforcement, and event tracking happen server-side. Billable event records and campaign spend are stored in MySQL, so daily budget checks survive restarts and work across backend workers.

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
├── docker-compose.prod.yml      Caddy HTTPS reverse proxy overlay
├── Caddyfile                    HTTPS routing for the production host
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
   - For CPM, `bid_amount >= reserve_price`; daily and total budgets must have room for spend.
   - Highest **priority** tier wins; ties are broken randomly.
4. The winner is emitted as `serve_ad`; otherwise `no_fill` with a reason (`missing_params`, `unauthorized`, or the selector's message).
5. The loader renders the creative, emits `impression` immediately and `click` on click, and adds a **report** control (⚑) so visitors can flag the ad.
6. `budget_tracker.py` records events at the campaign's CPM/CPC/CPA bid, **deduplicated per visitor, ad unit, event type, and UTC day** (`dedupe_key`), enforces campaign budgets from persisted events, and pushes `metric_update` and `live_event` messages to dashboards.

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
docker compose exec backend alembic upgrade head
```

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The compose file overrides `ADPLATFORM_DATABASE_URL` so both containers share one password. The backend is bound to host loopback; dashboards are not containerized. The production overlay and `PUBLIC_HOSTNAME` are only needed for a public HTTPS deployment.


### Production deployment

Set DNS for `PUBLIC_HOSTNAME` to this server and allow inbound TCP ports 80 and 443 (and UDP 443 for HTTP/3). Put MySQL credentials in the root `.env`, and production backend settings and Twilio credentials in `backend/.env`. Set the dashboard's HTTPS origin in `ADPLATFORM_CORS_ORIGINS`, set the public ad/media origin in `ADPLATFORM_PUBLIC_BASE_URL`, and use a strong random JWT secret. Then run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose exec backend alembic upgrade head
```

Caddy terminates TLS and proxies REST, media, and Socket.IO traffic to the backend. The backend port is only bound to host loopback. Keep the database and media volumes backed up. Deploy the React build or Flask dashboard separately behind HTTPS; run Flask with Gunicorn (`gunicorn --bind 0.0.0.0:5000 app:app`), not its development server. Production startup requires the implemented Twilio SMS provider, rejects localhost CORS and missing Razorpay credentials, and validates database/JWT settings.

### Running the backend locally

```bash
cd backend
python -m venv zenv
source zenv/bin/activate        # Windows: zenv\Scripts\activate

pip install -e ".[dev]"
cp .env.example .env            # edit values (see Configuration)
cp alembic.ini.example alembic.ini
alembic upgrade head
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
| `ADPLATFORM_SMS_BACKEND` | `console` (development) or `twilio` | `console` |
| `ADPLATFORM_TWILIO_ACCOUNT_SID` / `_AUTH_TOKEN` / `_FROM_NUMBER` | Twilio credentials and sender number when SMS backend is `twilio` | unset |
| `ADPLATFORM_REQUIRE_VERIFIED_MOBILE` | Block login and live sockets until the mobile is verified | `false` |
| `ADPLATFORM_ALLOW_SELF_SIGNUP` | Enable public account creation at `/api/auth/signup` | `true` |
| `ADPLATFORM_PUBLIC_BASE_URL` | Public base URL used when generating absolute media asset URLs; use the HTTPS origin visitors can reach | `http://localhost:8000` |
| `ADPLATFORM_RAZORPAY_KEY_ID` / `_KEY_SECRET` | Required for wallet top-ups | unset |

**Production guards:** with `ENVIRONMENT=production` the app refuses to start if the public base URL is localhost, SMS is not configured to use Twilio, CORS contains `*` or localhost, Razorpay credentials are missing, the database password is empty or a known weak value, or the JWT secret is weak. The built-in arithmetic CAPTCHA is enforced server-side on login, signup, OTP requests, and password reset, with signed challenges that expire after five minutes. The shipped `backend/.env.example` has a placeholder JWT secret and opts into development mode for local work.

**SMS:** Twilio is implemented. Production startup requires `ADPLATFORM_SMS_BACKEND=twilio` and all three Twilio settings above. Console delivery logs OTPs and is for development only.

**Public signup:** self signup is enabled by default. Set `ADPLATFORM_ALLOW_SELF_SIGNUP=false` to disable new public account creation while keeping sign-in available.

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

CPA conversions are reported server-to-server with the publisher key to `POST /api/delivery/events/conversion`.

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
| Public landing page with sign-in and signup links | ✔ (`/`) | ✔ (`/`) |
| Role-specific Home workspace | ✔ (`/home`) | ✔ (`/home`) |
| Login, signup, mobile verification, forgot password | ✔ | ✔ |
| Role-based navigation (admin / staff / publisher / advertiser) | ✔ | ✔ |
| Analytics (live counters + 7-day chart) | ✔ (`/analytics`) | ✔ (`/analytics`) |
| Campaigns: create, publish draft, pause/activate, delete | ✔ | ✔ (no publish button) |
| Creatives: add, toggle, review (admin), delete | ✔ (modal) | ✔ (page) |
| Publishers and ad slots | ✔ | ✔ |
| Approvals queue | ✔ | ✔ |
| Manage advertisers / publishers / ad slots / users (admin) | ✔ | ✔ |
| Visitor reports per ad slot | ✔ | ✘ |
| Live events feed (admin) | ✔ (sockets) | ✔ (polling) |
| Advertiser wallet top-up | ✔ (`/wallet`) | ✔ (`/wallet`) |
| Admin view of advertiser top-ups | ✔ (`/payments`) | ✘ |
| Publisher payouts (admin) | ✔ (`/payouts`) | ✔ (`/payments`) |

Route names differ: in the React app `/payments` is advertiser top-ups and `/payouts` is publisher payouts; in Flask `/payments` is publisher payouts. Both dashboards use `/` for the public landing page and `/home` for the authenticated workspace.

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

**Flask dashboard** (pytest):

```bash
cd dashboard-flask
python -m pytest -q
```

> The `dev` extra in `pyproject.toml` doesn't list `fakeredis`, which `egg-info` mentions from an older build. Redis is no longer used.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App exits at startup with a secret/production error | Weak or placeholder JWT secret, console SMS, local or wildcard CORS, missing Razorpay credentials, or weak DB password under production | Set production values, or use `ADPLATFORM_ENVIRONMENT=development` locally |
| Alembic cannot find its config | Copy `alembic.ini.example` to `alembic.ini` locally; Docker builds include the template automatically |
| Flask login works but session is lost on `http://localhost` | Secure cookies | Set `FLASK_INSECURE_COOKIES=1` for dev |
| Flask refuses to start | `FLASK_SECRET_KEY` shorter than 32 chars or contains "change" | Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| No OTP arrives | `SMS_BACKEND=console` or invalid Twilio settings | Use console only in development, or configure Twilio credentials and sender |
| `403 Mobile number not verified` | `REQUIRE_VERIFIED_MOBILE=true` | Complete verification at `/verify` |
| Ads never render, `no_fill` always | Publisher not active, ad unit not approved/active, no approved creative of the exact size, targeting mismatch, `bid_amount < reserve_price`, or cap exhausted | Check each in turn; the `no_fill` reason is logged server-side |
| Ad slot suddenly stops serving | 3 visitor reports moved it to `pending_review` | Review the reports in the admin slots page |
| Loader logs "Socket.IO client did not initialize" | Socket.IO client script not loaded first | Add the client `<script>` before `loader.js` |
| Dashboard shows "Disconnected" | `/socket.io` not proxied or token rejected | Check `vite.config.ts` proxy and that the user is active (and verified if required) |
| `NoReferencedTableError` in a script | Only some models imported | Import `app.models` (it registers all models) |
| Wallet "Razorpay is not configured" (503) | Missing Razorpay keys | Set `ADPLATFORM_RAZORPAY_KEY_ID` and `_KEY_SECRET` |

## Known gaps

Known business limitations:

- **Payout payment methods** (`stripe`, `paypal`, `wire_transfer`) are labels only; payouts are recorded and reconciled by an admin, with no payout gateway integrated.
- Campaign spend is attributed from the bid strategy (CPM impressions, CPC clicks, CPA conversions); publishers send conversions to `POST /api/delivery/events/conversion`. Publisher earnings accrue at the configured revenue share. Daily and total caps are checked against persisted event spend; unbudgeted campaigns debit the wallet per billable event, and budgeted campaigns spend from their reserved total. The HTTP event endpoint returns `402` when an event exceeds a cap or wallet funds; Socket.IO sends `event_rejected` for that event.
