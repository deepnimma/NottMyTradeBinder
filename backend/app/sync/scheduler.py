"""
APScheduler background job: poll eBay every N minutes.
"""
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()


def _run_sync():
    """Synchronous wrapper to run async sync engine from a background thread."""
    from app.database import SessionLocal
    from app.sync.engine import process_ebay_orders

    async def _sync():
        db = SessionLocal()
        try:
            ebay_count = await process_ebay_orders(db)
            if ebay_count:
                logger.info("Sync: processed %d eBay orders", ebay_count)
        except Exception as e:
            logger.error("Sync job error: %s", e)
        finally:
            db.close()

    asyncio.run(_sync())


def start_scheduler():
    if _scheduler.running:
        return
    interval = max(1, settings.sync_interval_minutes)
    _scheduler.add_job(_run_sync, "interval", minutes=interval, id="platform_sync", replace_existing=True)
    _scheduler.start()
    logger.info("Sync scheduler started (every %d min)", interval)


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
