from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.orders import router as order_router
from api.admin import router as admin_router
from api.analyst import router as analyst_router
from api.scheduler import start_auto_approval_scheduler, stop_auto_approval_scheduler
from config import CORS_ALLOW_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background job: auto-approve backlog orders that exceeded delay_minutes
    start_auto_approval_scheduler(interval_seconds=60)
    yield
    stop_auto_approval_scheduler()


app = FastAPI(
    title="Metro Cart Fraud Engine API",
    description="Backend services for order processing, rule configuration, and analyst reviews.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order_router, tags=["Orders"])
app.include_router(admin_router, tags=["Admin Panel"])
app.include_router(analyst_router, tags=["Analyst Portal"])


@app.get("/", tags=["Health Check"])
def root():
    return {"message": "✅ Metro Cart FastAPI is running securely."}
