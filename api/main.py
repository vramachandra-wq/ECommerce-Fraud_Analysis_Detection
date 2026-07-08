from fastapi import FastAPI

from api.orders import router as order_router
from api.admin import router as admin_router
from api.analyst import router as analyst_router

app = FastAPI(
    title="Metro Cart API",
    version="1.0.0"
)

app.include_router(order_router)
app.include_router(admin_router)
app.include_router(analyst_router)


@app.get("/")
def root():
    return {"message": "Metro Cart FastAPI is running"}