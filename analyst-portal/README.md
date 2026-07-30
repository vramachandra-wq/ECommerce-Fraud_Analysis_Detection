# Analyst Portal

Production serves the static portal from `static/analyst-portal/` via FastAPI:

```text
http://127.0.0.1:8000/portal/
```

Start the platform with:

```powershell
.\start.ps1
```

By default `start.ps1` does **not** rebuild from React, so hand-maintained static assets (SSO, rule matrix, IST scheduler labels, etc.) stay intact.

## Optional local React development

```powershell
cd analyst-portal
npm install
npm run dev
```

Vite proxies API calls to FastAPI on port 8000.

## Publishing the React build (opt-in)

This replaces files under `static/analyst-portal/`. Only do this when you intend the React app to be the served UI:

```powershell
.\start.ps1 -BuildPortal
# or
cd analyst-portal
npm run build
```
