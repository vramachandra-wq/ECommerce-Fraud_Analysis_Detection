from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.orders import router as order_router
from api.admin import router as admin_router
from api.analyst import router as analyst_router
from config import CORS_ALLOW_ORIGINS

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


@app.get("/", tags=["Health Check"])
def root():
    return {"message": "✅ Metro Cart FastAPI is running securely."}