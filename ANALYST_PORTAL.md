# Analyst Portal — No Node.js Required

Use this guide on a **company laptop** where you cannot install Node.js.

You have **two options** that only need **Python** (already used by this project).

---

## Option 1: Web portal (recommended)

A browser-based analyst UI is built into the project. It runs from FastAPI — **no npm, no Node, no admin rights**.

### Start

**Windows:** double-click `run_analyst_portal.bat`  
**Or in terminal:**

```bash
uvicorn api.main:app --reload
```

### Open in browser

```
http://127.0.0.1:8000/portal/
```

Log in with your analyst username and password from the database.

### What you get

Same features as `analyst_app.py` (Streamlit):

- Fraud review queue (approve / reject / batch)
- Admin panel (blacklists, permissions, users, analytics, rules)
- Power BI embed
- AI chatbot

Files: `static/analyst-portal/` (HTML + CSS + JavaScript, no build step).

---

## Option 2: Streamlit (already in project)

If you prefer the original UI:

```bash
streamlit run analyst_app.py --server.port 8502
```

Open: **http://localhost:8502**

---

## What you do NOT need

| Tool | Needed? |
|------|---------|
| Node.js | **No** |
| npm | **No** |
| `analyst-portal/` React folder | **No** (optional; only if Node is allowed later) |
| Admin / installer rights | **No** |

---

## Troubleshooting

**Page not loading**

1. Confirm API is running: open http://127.0.0.1:8000/ — you should see a JSON message with `"analyst_portal": "/portal/"`.
2. Use **port 8000**, not 5173 (5173 is only for React + Node).

**Login fails**

- Check PostgreSQL is running (`podman-compose up -d`).
- Use valid analyst credentials from `master.analyst_users`.

**Blank page at /portal/**

- Hard refresh (Ctrl+F5).
- Check browser console (F12) for errors.

---

## Full stack (first time)

```bash
podman-compose up -d
uvicorn api.main:app --reload
```

Then open **http://127.0.0.1:8000/portal/**
