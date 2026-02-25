"""
Webhook receivers for eBay ItemSold and future TCGPlayer notifications.
"""
from fastapi import APIRouter, Request, BackgroundTasks
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/ebay")
async def ebay_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives eBay Platform Notifications (ItemSold, etc.).
    eBay sends a POST with JSON body. Must respond 200 quickly; processing is async.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    logger.info("eBay webhook: %s", payload.get("metadata", {}).get("topic", "unknown"))

    topic = payload.get("metadata", {}).get("topic", "")
    if "ITEM_SOLD" in topic.upper() or "ORDER" in topic.upper():
        background_tasks.add_task(_process_ebay_webhook, payload)

    return {"status": "received"}


async def _process_ebay_webhook(payload: dict):
    from app.database import SessionLocal
    from app.sync.engine import on_sale
    db = SessionLocal()
    try:
        order_data = payload.get("notification", {}).get("data", {})
        if order_data:
            await on_sale("ebay", order_data, db)
    except Exception as e:
        logger.error("eBay webhook processing error: %s", e)
    finally:
        db.close()
