"""
eBay listing management + OAuth flow endpoints.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.integrations import ebay as ebay_client
from app.models.inventory import InventoryItem

router = APIRouter(prefix="/api/ebay", tags=["ebay"])

# eBay condition mapping
CONDITION_MAP = {
    "NM": "LIKE_NEW",
    "LP": "VERY_GOOD",
    "MP": "GOOD",
    "HP": "ACCEPTABLE",
}


@router.get("/auth-url")
def get_auth_url():
    """Returns the eBay OAuth authorization URL for the seller to visit."""
    try:
        url = ebay_client.get_auth_url()
        return {"auth_url": url}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback")
async def ebay_callback(code: str = Query(...)):
    """
    eBay redirects here after seller authorization.
    Exchanges the code for access + refresh tokens.
    """
    await ebay_client.exchange_code(code)
    # Redirect to frontend settings page
    return RedirectResponse(url="/#/settings?ebay=connected")


@router.get("/status")
def ebay_status():
    """Check if eBay is authenticated."""
    is_authed = ebay_client._access_token is not None
    return {"authenticated": is_authed}


@router.post("/list/{item_id}")
async def list_on_ebay(item_id: int, db: Session = Depends(get_db)):
    """Create an eBay inventory item + offer and publish it."""
    item = db.scalar(
        select(InventoryItem).options(joinedload(InventoryItem.card)).where(InventoryItem.id == item_id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.ebay_price is None:
        raise HTTPException(status_code=400, detail="Set ebay_price before listing")

    card = item.card
    sku = f"{card.game}-{card.set_id}-{card.card_number}-{item.condition}"
    title = f"{card.name} [{card.set_name}] {item.condition} Pokemon TCG" if card.game == "pokemon" else f"{card.name} [{card.set_name}] {item.condition}"
    description = f"{card.name} from {card.set_name}. Condition: {item.condition}. Card #{card.card_number}."

    ebay_condition = CONDITION_MAP.get(item.condition, "LIKE_NEW")

    # Create/replace inventory item
    await ebay_client.create_or_replace_inventory_item(
        sku=sku,
        title=title[:80],  # eBay title limit
        description=description,
        quantity=item.quantity,
        image_url=card.image_url,
        condition=ebay_condition,
    )

    # Create offer
    offer_resp = await ebay_client.create_offer(sku=sku, price=float(item.ebay_price))
    offer_id = offer_resp.get("offerId")
    if not offer_id:
        raise HTTPException(status_code=500, detail=f"eBay offer creation failed: {offer_resp}")

    # Publish offer → live listing
    await ebay_client.publish_offer(offer_id)

    item.ebay_inventory_sku = sku
    item.ebay_offer_id = offer_id
    item.listed_on_ebay = True
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "listed", "sku": sku, "offer_id": offer_id}


@router.post("/delist/{item_id}")
async def delist_from_ebay(item_id: int, db: Session = Depends(get_db)):
    """Withdraw an eBay listing."""
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if not item.ebay_offer_id:
        raise HTTPException(status_code=400, detail="No eBay offer ID on file")

    await ebay_client.delist_offer(item.ebay_offer_id)
    item.listed_on_ebay = False
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "delisted"}


@router.post("/orders/sync")
async def sync_ebay_orders(db: Session = Depends(get_db)):
    """Manually trigger an eBay order poll and process new sales."""
    from app.sync.engine import process_ebay_orders
    processed = await process_ebay_orders(db)
    return {"processed": processed}
