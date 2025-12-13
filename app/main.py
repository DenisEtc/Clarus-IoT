from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.predictions import router as predictions_router

app = FastAPI(title="Clarus-IoT", version="0.1.0")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(billing_router, prefix="/billing", tags=["billing"])
app.include_router(predictions_router, prefix="/predictions", tags=["predictions"])


@app.get("/health")
def health():
    return {"status": "ok"}
