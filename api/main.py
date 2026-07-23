from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.orders import router as order_router
from api.admin import router as admin_router
from api.analyst import router as analyst_router
from api.portal import router as portal_router
from config import CORS_ALLOW_ORIGINS

PORTAL_STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "analyst-portal"

# 1. Added a description for better documentation in /docs
app = FastAPI(
    title="Metro Cart Fraud Engine API",
    description="Backend services for order processing, rule configuration, and analyst reviews.",
    version="1.0.0"
)

# 2. CORS Middleware Configuration (CRITICAL FOR STREAMLIT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Added 'tags' so your Swagger UI (/docs) groups endpoints neatly by category
app.include_router(order_router, tags=["Orders"])
app.include_router(admin_router, tags=["Admin Panel"])
app.include_router(analyst_router, tags=["Analyst Portal"])
app.include_router(portal_router, tags=["React Portal"])

if PORTAL_STATIC_DIR.is_dir():
    app.mount(
        "/portal",
        StaticFiles(directory=str(PORTAL_STATIC_DIR), html=True),
        name="analyst-portal",
    )


@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "Metro Cart FastAPI is running securely.",
        "analyst_portal": "/portal/",
    }