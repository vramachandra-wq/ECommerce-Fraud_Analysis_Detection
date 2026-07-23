# Metro Cart Analyst Portal

Two ways to run the analyst UI (replacement for `analyst_app.py`):

## Option 1 — No Node.js (recommended if npm is not installed)

Start only the API:

```bash
uvicorn api.main:app --reload
```

Open:

```
http://127.0.0.1:8000/portal/
```

Static files live in `static/analyst-portal/` and are served by FastAPI.

## Option 2 — React dev server (requires Node.js 18+)

Install Node.js from https://nodejs.org/ then:

## Environment

Copy `.env.example` to `.env` in the project root and set:

```env
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000` (see `vite.config.ts`).

For production builds, set `VITE_API_BASE_URL` to your deployed API URL.

## Features (parity with Streamlit `analyst_app.py`)

| Page | Route |
|------|-------|
| Fraud Analyst Dashboard | `/dashboard` |
| Admin Control Panel | `/admin` |
| Analytics Dashboards (Power BI) | `/analytics` |
| AI Chatbot | `/chatbot` |

RBAC uses the same `master.analyst_permissions` page keys as the Streamlit app.

## API endpoints added for the React UI

- `POST /auth/login`, `GET /auth/me`
- `GET /portal/queue`, `GET /portal/orders/{id}`
- `GET /portal/analytics/*`, `GET /portal/permissions`, `GET /portal/rules`
- `POST /portal/chat`
- Existing mutation endpoints: `/approve-order`, `/blacklist-ip`, etc.

See Swagger at **http://127.0.0.1:8000/docs**.
