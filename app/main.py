from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from app.database import engine, Base, get_db
from app.models import models
from app.api.endpoints import router as deals_router, receive_webhook
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.jobs import scheduler, auto_release_expired_deals
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs when the server starts
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.add_job(auto_release_expired_deals, "interval", hours=1)
    scheduler.start()

    yield  # App handles requests here

    # Runs when the server shuts down
    scheduler.shutdown()
    await engine.dispose()


app = FastAPI(
    title="EscrowPay",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "EscrowPay"}

@app.post("/webhook")
async def webhook_alias(request: Request, db: AsyncSession = Depends(get_db)):
    return await receive_webhook(request, db)