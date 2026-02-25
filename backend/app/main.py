from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import cards, inventory, orders, settings, webhooks, ebay

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Start background scheduler (wired up in Phase 5)
    try:
        from app.sync.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
        logger.info("Sync scheduler started")
    except Exception as e:
        logger.warning("Scheduler not started: %s", e)

    yield

    try:
        from app.sync.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="NottMyTradeBinder",
    description="TCGPlayer + eBay inventory manager for Pokémon and Weiss Schwarz",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production with specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(settings.router)
app.include_router(webhooks.router)
app.include_router(ebay.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
