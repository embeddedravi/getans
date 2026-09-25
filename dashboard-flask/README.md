# Flask Dashboard — Ad Platform

## Stack
- **Flask** (Python 3.12) — server-side rendering with Jinja2
- **Tailwind CSS v3** + **DaisyUI v4** — compiled via Tailwind CLI
- **Chart.js** (CDN) — analytics charts
- Proxies all API requests to the **FastAPI** backend

## Setup

### 1. Install Python dependencies
```bash
py -m pip install flask requests python-dotenv
```

### 2. Install Tailwind + DaisyUI (Node/npm)
```bash
cd dashboard-flask
npm install
```

### 3. Build CSS
```bash
npm run build:css
# or watch mode:
npm run watch:css
```

### 4. Configure environment
Copy `.env.example` to `.env` and fill in values:
```
FLASK_SECRET_KEY=your-random-secret
API_BASE_URL=http://localhost:8000/api
```

### 5. Run Flask
```bash
py app.py
# or with flask CLI:
flask run --port 5000
```

Open http://localhost:5000

## Project structure
```
dashboard-flask/
├── app.py                  # Flask routes & API proxy
├── tailwind.config.js      # Tailwind + DaisyUI theme
├── package.json            # npm scripts for CSS build
├── .env.example
├── templates/
│   ├── base.html           # Root HTML, flash messages
│   ├── layout.html         # Sidebar + topbar shell
│   ├── login.html          # Login page
│   ├── analytics.html      # Analytics (Chart.js)
│   ├── campaigns.html      # Campaigns CRUD
│   └── publishers.html     # Publishers & ad slots
└── static/
    └── css/
        ├── input.css       # Tailwind source
        └── main.css        # Compiled output (git-ignored)
```

## Pages
| Route | Page |
|-------|------|
| `/login` | Sign in (proxies to FastAPI JWT) |
| `/` | Analytics — live counters + bar chart |
| `/campaigns` | Campaign list, create, toggle, delete |
| `/publishers` | Publisher list + ad slot management |
| `/logout` | Clears session |
