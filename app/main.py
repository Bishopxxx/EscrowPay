from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from app.database import engine, Base, get_db
from app.models import models
from app.api.endpoints import router as deals_router, receive_webhook
from sqlalchemy.ext.asyncio import AsyncSession

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs when the server starts
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield # The app handles requests here
    
    # Runs when the server shuts down
    await engine.dispose()

app = FastAPI(
    title="EscrowPay", 
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(deals_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "EscrowPay"}


@app.post("/webhook")
async def webhook_alias(request: Request, db:AsyncSession=Depends(get_db)):
    return await receive_webhook(request, db)