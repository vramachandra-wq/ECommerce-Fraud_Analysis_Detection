# Analyst Portal — React source → static build

The production analyst UI is a **React app** in `analyst-portal/` that builds into `static/analyst-portal/` and is served by FastAPI at `/portal/`.

Streamlit analyst/customer apps have been removed. The customer shop remains at `/shop/` (`static/customer-portal/`).

---

## First-time build (requires Node.js 18+)

From the project root:

```powershell
.\scripts\build_analyst_portal.ps1
```

Or manually:

```powershell
cd analyst-portal
npm install
npm run build
```

Then start the API:

```powershell
uvicorn api.main:app --reload
```

Open: **http://127.0.0.1:8000/portal/**

---

## Development (hot reload)

Terminal 1 — API:

```powershell
uvicorn api.main:app --reload
```

Terminal 2 — Vite dev server (proxies `/api` → `:8000`):

```powershell
cd analyst-portal
npm run dev
```

Open: **http://127.0.0.1:5173**

Set in project `.env` when using Vite:

```env
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## After changing React source

Re-run `.\scripts\build_analyst_portal.ps1` before deploying or sharing the static bundle.

FastAPI serves whatever is in `static/analyst-portal/` — it does not auto-build on `start.ps1`.

---

## Features

| Page | Route |
|------|-------|
| Fraud Analyst Dashboard | `/portal/dashboard` |
| Admin Control Panel | `/portal/admin` |
| Analytics Dashboards (Power BI) | `/portal/analytics` |
| AI Chatbot | `/portal/chatbot` |

Admin → **Audit Log** tab shows `master.order_review_audit` (approve/reject/auto-approve history).

RBAC uses `master.analyst_permissions` page keys.

---

## API

- `POST /auth/login`, `GET /auth/me`
- `GET /portal/queue`, `GET /portal/audit`, …
- Swagger: **http://127.0.0.1:8000/docs**
