# Ad Platform

A self-hosted ad server and management platform: publishers embed a
lightweight snippet, ads are delivered in real time over Socket.IO, and
campaigns/creatives/analytics are managed through a REST API + dashboard.

## Structure

- `backend/` — FastAPI + Socket.IO server (ad delivery, campaign CRUD, analytics)
- `publisher-snippet/` — embeddable JS loader for publisher sites
- `dashboard/` — (not yet built) campaign management + live analytics UI

## Quickstart

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Then run migrations:

```bash
docker compose exec backend alembic upgrade head
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health

## Embedding on a publisher site

```html
<div data-ad-unit-id="123"></div>
<script src="http://localhost:8000/static/loader.js"
        data-api-key="PUBLISHER_API_KEY"
        data-server="http://localhost:8000"></script>
```

(Serve `publisher-snippet/src/loader.js` as a static file, or bundle/minify it
as part of your build.)

## Status

- [x] Data model + migrations
- [x] Ad selection (targeting + budget + priority)
- [x] Real-time delivery over Socket.IO
- [x] Campaign/creative/publisher REST CRUD + JWT auth
- [x] Event tracking + real-time budget decrement
- [x] Live dashboard metrics relay (Socket.IO + Redis pub/sub)
- [ ] Dashboard frontend
- [ ] Tests
