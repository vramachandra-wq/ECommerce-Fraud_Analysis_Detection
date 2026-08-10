from contextlib import asynccontextmanager
import logging
from pathlib import Path

import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.orders import router as order_router
from api.admin import router as admin_router
from api.analyst import router as analyst_router
from api.portal import router as portal_router
from api.customer_shop import router as customer_shop_router
from api.scheduler import start_auto_approval_scheduler, stop_auto_approval_scheduler
from config import BACKLOG_ALERT_INTERVAL_MINUTES, CORS_ALLOW_ORIGINS

PORTAL_DIR = Path(__file__).resolve().parent.parent / "static" / "analyst-portal"
SHOP_DIR = Path(__file__).resolve().parent.parent / "static" / "customer-portal"


def _ensure_schema_on_startup() -> None:
    """Apply SQL migrations + ensure tables; never fail silently."""
    from database.migrate import apply_sql_migrations
    from database.order_items import ensure_order_items_table
    from database.system_audit import ensure_system_audit_table
    from utils.system_audit import import_file_audit_logs_if_empty

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            applied, skipped = apply_sql_migrations(cur)
            if applied:
                logger.info("Applied migrations: %s", ", ".join(applied))
            elif skipped:
                logger.info("Migrations already applied (%d files)", len(skipped))
            # Idempotent safety net for DBs that predate the migrator.
            ensure_order_items_table(cur)
            ensure_system_audit_table(cur)
            import_file_audit_logs_if_empty(cur)
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_secrets()
    log_security_posture()

    try:
        _ensure_schema_on_startup()
    except psycopg2.OperationalError as exc:
        logger.warning(
            "Database unavailable at startup (schema ensure skipped): %s",
            exc,
        )
        if SCHEMA_STRICT:
            raise
    except Exception:
        logger.exception("Schema ensure / migration failed at startup")
        if SCHEMA_STRICT:
            raise

    # Background job: backlog email digest + auto-approve expired review-queue orders
    start_auto_approval_scheduler(
        interval_seconds=max(60, int(BACKLOG_ALERT_INTERVAL_MINUTES) * 60)
    )
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
        "health": "/health",
    }


@app.get("/health", tags=["Health Check"])
def health():
    """Liveness + database readiness probe for deploy / orchestration."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {"status": "ok", "database": "up"}
    except Exception as exc:
        logger.warning("Health check database probe failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "down",
                "detail": str(exc.__class__.__name__),
            },
        )


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
