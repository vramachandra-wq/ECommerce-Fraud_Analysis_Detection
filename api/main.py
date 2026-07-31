from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.orders import router as order_router
from api.admin import router as admin_router
from api.analyst import router as analyst_router
from api.portal import router as portal_router
from api.customer_shop import router as customer_shop_router
from api.scheduler import start_auto_approval_scheduler, stop_auto_approval_scheduler
from config import CORS_ALLOW_ORIGINS

PORTAL_DIR = Path(__file__).resolve().parent.parent / "static" / "analyst-portal"
SHOP_DIR = Path(__file__).resolve().parent.parent / "static" / "customer-portal"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure multi-item order + system audit schema exist on existing databases.
    try:
        import psycopg2
        from config import DB_CONFIG
        from database.order_items import ensure_order_items_table
        from database.system_audit import ensure_system_audit_table
        from utils.system_audit import import_file_audit_logs_if_empty

        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                ensure_order_items_table(cur)
                ensure_system_audit_table(cur)
                import_file_audit_logs_if_empty(cur)
            conn.commit()
    except Exception:
        # Startup should not crash if DB is briefly unavailable; place-order also ensures.
        pass

    # Background job: auto-approve backlog orders that exceeded delay_minutes
    start_auto_approval_scheduler(interval_seconds=1800)
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
# Portal API routes must be registered before the /portal static mount.
app.include_router(portal_router, tags=["Web Portal"])
app.include_router(customer_shop_router, tags=["Customer Shop"])


@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "✅ Metro Cart FastAPI is running securely.",
        "analyst_portal": "/portal/",
        "customer_portal": "/shop/",
    }


@app.get("/portal", include_in_schema=False)
@app.get("/portal/", include_in_schema=False)
def portal_index():
    return FileResponse(PORTAL_DIR / "index.html")


@app.get("/shop", include_in_schema=False)
@app.get("/shop/", include_in_schema=False)
def shop_index():
    return FileResponse(SHOP_DIR / "index.html")


app.mount(
    "/portal",
    StaticFiles(directory=str(PORTAL_DIR), html=True),
    name="analyst_portal",
)

app.mount(
    "/shop",
    StaticFiles(directory=str(SHOP_DIR), html=True),
    name="customer_portal",
)
