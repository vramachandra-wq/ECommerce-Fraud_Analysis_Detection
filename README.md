# Metro Cart — E-Commerce Fraud Detection & Analytics Platform

Real-time, rule-based fraud detection for e-commerce orders. The platform evaluates every purchase against configurable rules, automates hold/review/reject decisions, supports analyst investigation, and exposes analytics through Streamlit portals, FastAPI, Power BI, and an AI chatbot.

---

# Overview

When a customer places an order, the fraud engine applies rules from `master.rule_master` and can:

- Approve the order
- Hold the order (`ON_HOLD`)
- Send the order for manual review (`PENDING_REVIEW`)
- Reject the order

Held and review orders wait for `rule_master.delay_minutes`. After that window they become **backlog** and can be handled by analysts or **auto-approved** by the API scheduler on timeout.

Also included:

- Customer purchase portal
- Fraud Analyst Workspace (queue + backlog)
- Admin Control Panel (users, permissions, rules, blacklists, analytics)
- RBAC page permissions
- AI analytics chatbot (Groq)
- Power BI dashboards
- English / Thai UI language toggle
- bcrypt-hashed passwords

---

# Features

## Real-time fraud detection

- Configurable static, velocity, behavioral, and linkage rules
- Review timeout driven by `delay_minutes` (R001 default **180**; others typically **60**)
- Max delay across triggered rules for multi-hit orders
- Background auto-approval of expired holds/reviews (~60s)

## Analyst portal

- Pending review / hold queue and backlog management
- Individual and bulk approve / reject / flag fraud (with confirmations)
- Remaining-time timers and overdue highlighting
- Change password from the **login page** (username + current password → new password → log in again)

## Admin panel

- Create analyst accounts (passwords hashed with bcrypt)
- Page permissions and roles
- Rule thresholds, intervals, and delay minutes (R001: delay only)
- IP / email / phone blacklist management
- KPI and rule analytics

## AI chatbot

- Natural-language questions over orders, fraud, revenue, customers, products, devices, and rules
- SQL generation + validation (SELECT-only) via Groq
- Charts and follow-up suggestions
- Sensitive fields (`email`, `phone`, `address`, `ip`) masked in tables, charts, history, and logs

## Localization & UX

- UI language: English / Thai (chatbot answers stay in English)
- Currency display: Thai Baht (฿)

---

# Fraud detection rules

| Rule | Description | Typical action |
|------|-------------|----------------|
| P2 iPhone 16 Rule | High-risk product monitoring | Hold |
| Email Velocity | Multiple orders from the same email | Review |
| IP Velocity | Multiple orders from the same IP | Review |
| Device Velocity | Multiple orders from the same device | Review |
| User Spend Velocity | Spending exceeds threshold | Review |
| Multiple Users Same Email | Same email linked to multiple users | Review |
| Blacklisted IP | IP present in blacklist | Reject |
| Burst Orders | Multiple orders within a short duration | Review |
| Address Velocity | Multiple deliveries to the same address | Review |
| Device Switching | Frequent device changes | Review |
| Blacklisted Phone Number | Phone present in blacklist | Reject |
| Blacklisted Email | Email present in blacklist | Reject |

---

# Technology stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI (+ lifespan auto-approval scheduler) |
| Database | PostgreSQL 15 (Podman Compose) |
| Frontends | Streamlit (`customer_app.py`, `analyst_app.py`) |
| Analytics | Power BI embed |
| AI | Groq API |
| Auth | bcrypt |
| Language | Python 3.10+ |
| Containers | Podman / podman-compose |

---

# Project structure

```text
ECommerce-Fraud_Analysis_Detection/
├── ai/                         # Chatbot + Groq client + prompts
├── api/                        # FastAPI routes + scheduler
├── auth/                       # Customer / analyst auth + password hashing
├── database/                   # Connection pool + repositories
├── fraud_engine/               # Rules, engine, backlog, auto-approval, audit
├── images/                     # UI assets
├── init_scripts/ecommerce_fraud/
│   └── schema.sql              # Full DDL + seed (Compose init)
├── portals/                    # Streamlit pages (customer, analyst, admin, chatbot, …)
├── scripts/
│   └── hash_seed_passwords.py  # Optional: bcrypt-hash live/seed passwords
├── tests/                      # Unit + integration tests
├── ui/                         # Theme + i18n
├── utils/                      # Queries, PII helpers, order utils
├── analyst_app.py
├── customer_app.py
├── config.py
├── podman-compose.yaml
├── requirements.txt
├── start.ps1                   # Start DB + API + portals
├── stop.ps1                    # Stop everything
└── README.md
```

---

# Getting started

## Prerequisites

- Python 3.10+
- Podman (with `podman-compose` available — `pip install podman-compose` if needed)
- Chrome (optional; `start.ps1` opens portals)

## Quick start (Windows)

From the project root in PowerShell:

```powershell
.\start.ps1
```

First run will:

1. Create `.venv` and install `requirements.txt`
2. Create `.env` from `.env.example` if missing
3. Start PostgreSQL via `podman-compose.yaml`
4. Start FastAPI (`:8000`) and Streamlit apps (`:8501`, `:8502`)
5. Open the service URLs in Chrome

Stop everything:

```powershell
.\stop.ps1
```

### Service URLs

| Service | URL |
|---------|-----|
| API docs | http://127.0.0.1:8000/docs |
| Customer portal | http://localhost:8501 |
| Analyst portal | http://localhost:8502 |

App logs: `.run/logs/`

### Demo logins (seed data)

| Portal | ID / username | Password |
|--------|---------------|----------|
| Customer | `U1001` | `password123` |
| Analyst | `analyst` | `secure123` |
| Admin | `admin` | `admin123` |

Passwords are stored as **bcrypt** hashes. Change password is available on the analyst **login** screen.

## Environment

Copy `.env.example` → `.env` and set at least:

| Variable | Purpose |
|----------|---------|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | App DB connection |
| `POSTGRES_*` / same credentials | Compose Postgres |
| `GROQ_API_KEY` | AI chatbot (required for chatbot answers) |
| `API_BASE_URL` | Streamlit → FastAPI (default `http://127.0.0.1:8000`) |
| `POWER_BI_EMBED_URL` | Optional Power BI embed |

## Database initialization

Compose mounts `init_scripts/ecommerce_fraud/` → `/docker-entrypoint-initdb.d`.

Postgres runs `schema.sql` **once** when the data volume is empty (rules with `delay_minutes`, backlog indexes, `order_review_audit`, seed users/orders).

Rebuild DB from scratch:

```powershell
podman-compose -f podman-compose.yaml down -v
.\start.ps1
```

Without `-v`, the existing volume is kept and init scripts are **not** re-run.

Optional helper to bcrypt-hash any remaining plain-text passwords:

```powershell
.\.venv\Scripts\python.exe scripts\hash_seed_passwords.py
```

## Manual setup (optional)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env   # edit DB_* / GROQ_API_KEY
podman-compose -f podman-compose.yaml up -d
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
streamlit run customer_app.py --server.port 8501
streamlit run analyst_app.py --server.port 8502
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## pgAdmin (optional)

| Parameter | Value |
|-----------|-------|
| Host | `localhost` |
| Port | `5434` (or `DB_PORT` from `.env`) |
| Database | `DB_NAME` / `POSTGRES_DB` |
| Username | `DB_USER` / `POSTGRES_USER` |
| Password | `DB_PASSWORD` / `POSTGRES_PASSWORD` |

---

# User roles

## Customer

- Place orders
- Track order status

## Fraud analyst

- Review holds / pending reviews / backlog
- Approve, reject, or flag fraud
- Use AI chatbot and allowed dashboards (per permissions)

## Administrator

- Manage analysts and page permissions
- Configure rules and delay minutes
- Manage blacklists
- Full portal access

---

# Platform workflow

```text
                 Customer Places Order
                         │
                         ▼
               Real-Time Fraud Engine
                         │
                         ▼
        ┌──────────────────────────────────┐
        │ Approve │ Hold │ Review │ Reject │
        └──────────────────────────────────┘
                         │
                         ▼
         Delay window (rule_master.delay_minutes)
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
     Analyst Workspace         Auto-approval
     (backlog / review)        (after timeout)
            │
            ▼
     Final status + order_review_audit
```

---

# Security

- RBAC page permissions
- bcrypt password hashing (create user + change password + seed data)
- Legacy plain-text passwords upgraded on successful login when present
- IP / email / phone blacklists
- Chatbot PII masking for email, phone, address, and IP in UI/charts/logs
- Analyst password change on the login page (verified current password required)
