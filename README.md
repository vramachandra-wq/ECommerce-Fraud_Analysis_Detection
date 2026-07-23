# 🛒 E-Commerce Real-Time, Rule-Based Fraud Detection & Analytics Platform

A real-time, rule-based fraud detection platform for e-commerce transactions that detects suspicious orders, automates fraud decisions, streamlines analyst investigations, and provides actionable insights through integrated analytics dashboards.

---

# 📌 Overview

The platform evaluates every customer order against configurable fraud detection rules before order fulfillment. Based on the triggered rules, the system can automatically:

- ✅ Approve the order
- ⏳ Hold the order
- 🔍 Send the order for manual review
- ❌ Reject the order

The platform also provides:

- Fraud Analyst Portal
- Admin Panel
- Rule Management System
- Role-Based Access Control (RBAC)
- Blacklist Management
- AI Analytics Chatbot
- Integrated Power BI Dashboards

---

# ✨ Features

## Real-Time Fraud Detection

- Rule-based fraud detection engine
- Configurable fraud rules
- Automatic fraud decisioning
- Real-time order evaluation

## Fraud Analyst Portal

Fraud analysts can:

- Review suspicious orders
- Approve orders
- Reject orders
- Flag fraudulent orders
- View order history

## Admin Panel

Administrators can:

- Create analyst accounts
- Manage users
- Assign permissions
- Manage dashboard access
- Modify fraud rule thresholds
- Update rule time intervals
- Manage blacklist entries

## Rule Management

Supports configurable fraud rules including:

- Static Rules
- Velocity Rules
- Behavioral Rules
- Linkage Rules

## Blacklist Management

Maintain blacklists for:

- IP Addresses
- Email Addresses
- Phone Numbers

Blacklisted entities are automatically rejected during order evaluation.

## Analytics

Integrated Power BI dashboards provide insights into:

- Fraud trends
- Rule trigger frequency
- Order status distribution
- Analyst workload
- Fraud investigation metrics

## AI Chatbot

Natural language interface for querying fraud and order-related data.

---

# 📋 Fraud Detection Rules

| Rule | Description | Action |
|------|-------------|--------|
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

# 🏗️ Technology Stack

| Component | Technology |
|------------|------------|
| Backend API | FastAPI |
| Database | PostgreSQL |
| Frontend | Streamlit |
| Analytics | Power BI |
| AI Integration | Groq API |
| Programming Language | Python |
| Containerization | Podman |

---

# 📁 Project Structure

```text
ECOMMERCE-FRAUD_ANALYSIS_DETECTION/
│
├── ai/                    # AI chatbot and Groq integration
├── api/                   # FastAPI endpoints
├── auth/                  # Authentication modules
├── data_csv/              # Sample datasets
├── database/              # Database connection and repositories
├── fraud_engine/          # Fraud detection engine and rules
├── images/                # UI assets
├── init_scripts/          # Database initialization scripts
├── portals/               # Streamlit portal components
├── ui/                    # UI styling
├── utils/                 # Utility functions
│
├── analyst_app.py         # Fraud Analyst Streamlit application
├── customer_app.py        # Customer Streamlit application
├── config.py
├── podman-compose.yaml
├── requirements.txt
└── README.md
```

---

# 🚀 Getting Started

## 1. Clone the Repository

```bash
https://github.com/vramachandra-wq/ECommerce-Fraud_Analysis_Detection.git
```

---

## 2. Create a Python Virtual Environment

### Windows

```bash
python -m venv .venv
```

### Linux / macOS

```bash
python3 -m venv .venv
```

---

## 3. Activate the Virtual Environment

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

---

## 4. Install the Required Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Start the PostgreSQL Database

Build and start the Podman containers:

```bash
podman-compose up -d
```

Verify the containers are running:

```bash
podman ps
```

---

## 6. Access the Database Using pgAdmin (Optional)

To inspect the database using **pgAdmin**, register a new server with the following configuration.

| Parameter | Value |
|-----------|-------|
| **Server Name** | `ecommerce_fraud` |
| **Host Name / Address** | `localhost` |
| **Port** | `5434` |
| **Maintenance Database** | `postgres` (or your configured database) |
| **Username** | Value of `POSTGRES_USER` from the `.env` file |
| **Password** | Value of `POSTGRES_PASSWORD` from the `.env` file |

After registering the server, you can browse the schemas, tables, views, and execute SQL queries directly from pgAdmin.

---

## 7. Start the FastAPI Backend

Open a new terminal, activate the virtual environment, and start the FastAPI service:

```bash
uvicorn api.main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

---

## 8. Launch the Streamlit Applications

Open **two separate terminals**, activate the Python virtual environment in both, and run the following commands.

### Terminal 1 – Customer Portal

```bash
streamlit run customer_app.py --server.port 8501
```

Customer Portal:

```
http://localhost:8501
```

---

### Terminal 2 – Fraud Analyst Portal

**Option A — Web UI (no Node.js required)**

```bash
uvicorn api.main:app --reload
```

Analyst Portal (served by FastAPI):

```
http://127.0.0.1:8000/portal/
```

**Option B — React dev server (requires Node.js 18+)**

```bash
uvicorn api.main:app --reload
cd analyst-portal
npm install
npm run dev
```

React Analyst Portal:

```
http://localhost:5173
```

See `analyst-portal/README.md` for React setup. Use Option A if Node.js is not installed.

**Option C — Streamlit UI (legacy)**

```bash
streamlit run analyst_app.py --server.port 8502
```

Fraud Analyst Portal (Streamlit):

```
http://localhost:8502
```

---

# 👥 User Roles

> **Company laptop / no Node.js?** See **[ANALYST_PORTAL.md](ANALYST_PORTAL.md)** — use `http://127.0.0.1:8000/portal/` or double-click `run_analyst_portal.bat`. Node.js is **not** required.

## Customer

- Place orders
- Track order status

## Fraud Analyst

- Review suspicious orders
- Approve orders
- Reject orders
- Flag fraudulent orders
- Investigate rule triggers

## Administrator

- Create and manage analyst accounts
- Configure fraud rules
- Modify thresholds and time intervals
- Manage blacklist entries
- Assign dashboard permissions
- Manage platform access

---

# 📊 Platform Workflow

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
              Fraud Analyst Portal
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Approve        Reject       Flag Fraud
                         │
                         ▼
                 Final Order Status
```

---

# 🔒 Security Features

- Role-Based Access Control (RBAC)
- Secure User Authentication
- IP Address Blacklisting
- Email Address Blacklisting
- Phone Number Blacklisting
- Configurable Rule-Based Fraud Detection
- Administrative Access Control

---