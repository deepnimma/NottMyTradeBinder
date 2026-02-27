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
from app.models.card import Card
from app.models.inventory import InventoryItem

router = APIRouter(prefix="/api/ebay", tags=["ebay"])

# eBay condition mapping
CONDITION_MAP = {
    "NM": "LIKE_NEW",
    "LP": "VERY_GOOD",
    "MP": "GOOD",
    "HP": "ACCEPTABLE",
}


def _make_sku(card: "Card", item: InventoryItem) -> str:
    variant_slug = item.variant.lower().replace(" ", "-")
    return f"{card.game}-{card.set_id}-{card.card_number}-{variant_slug}-{item.condition}"


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
    """Create or update an eBay inventory item + offer."""
    item = db.scalar(
        select(InventoryItem).options(joinedload(InventoryItem.card)).where(InventoryItem.id == item_id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.ebay_price is None:
        raise HTTPException(status_code=400, detail="Set ebay_price before listing")

    card = item.card
    sku = _make_sku(card, item)
    variant_label = f" ({item.variant})" if item.variant != "Normal" else ""
    title = f"{card.name}{variant_label} [{card.set_name}] {item.condition} Pokemon TCG" if card.game == "pokemon" else f"{card.name}{variant_label} [{card.set_name}] {item.condition}"
    description = f"{card.name} from {card.set_name}. Condition: {item.condition}. Card #{card.card_number}."
    ebay_condition = CONDITION_MAP.get(item.condition, "LIKE_NEW")

    # Always update/replace the inventory item record (idempotent PUT)
    await ebay_client.create_or_replace_inventory_item(
        sku=sku,
        title=title[:80],
        description=description,
        quantity=item.quantity,
        image_url=card.image_url,
        condition=ebay_condition,
    )

    if item.listed_on_ebay and item.ebay_offer_id and item.ebay_inventory_sku:
        # Already listed — update qty/price on existing offer, no new listing
        await ebay_client.update_quantity(
            sku=item.ebay_inventory_sku,
            offer_id=item.ebay_offer_id,
            new_quantity=item.quantity,
            price=float(item.ebay_price),
        )
        item.staged = False
        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "updated", "sku": sku, "offer_id": item.ebay_offer_id}
    else:
        # New listing — create offer and publish
        offer_resp = await ebay_client.create_offer(sku=sku, price=float(item.ebay_price))
        offer_id = offer_resp.get("offerId")
        if not offer_id:
            raise HTTPException(status_code=500, detail=f"eBay offer creation failed: {offer_resp}")
        await ebay_client.publish_offer(offer_id)
        item.ebay_inventory_sku = sku
        item.ebay_offer_id = offer_id
        item.listed_on_ebay = True
        item.staged = False
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


@router.post("/list-set/{game}/{set_id}")
async def list_set_on_ebay(game: str, set_id: str, db: Session = Depends(get_db)):
    """
    Create or update a multi-variation eBay listing for all inventory items in a set.
    If the set is already listed, updates inventory items and qty/price in place.
    """
    items = db.scalars(
        select(InventoryItem)
        .options(joinedload(InventoryItem.card))
        .join(Card)
        .where(Card.game == game, Card.set_id == set_id)
        .where(InventoryItem.ebay_price.is_not(None))
        .where(InventoryItem.quantity > 0)
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="No inventory items with eBay price in this set")

    set_name = items[0].card.set_name
    group_key = f"{game}-{set_id}-set"
    title = f"{set_name} Pokemon TCG Cards" if game == "pokemon" else f"{set_name} Cards"

    # Check if this set is already listed
    existing_offer_id = next((i.ebay_group_offer_id for i in items if i.ebay_group_offer_id), None)

    skus: list[str] = []
    aspect_card_names: list[str] = []
    aspect_card_numbers: list[str] = []
    aspect_conditions: list[str] = []
    aspect_variants: list[str] = []
    image_urls: list[str] = []
    min_price = float("inf")

    for item in items:
        card = item.card
        sku = _make_sku(card, item)
        ebay_condition = CONDITION_MAP.get(item.condition, "LIKE_NEW")

        await ebay_client.create_or_replace_inventory_item(
            sku=sku,
            title=f"{card.name} #{card.card_number}",
            description=f"{card.name} from {set_name}. #{card.card_number}. Condition: {item.condition}. Variant: {item.variant}.",
            quantity=item.quantity,
            image_url=card.image_url,
            condition=ebay_condition,
            aspects={
                "Card Name": [card.name],
                "Card Number": [card.card_number],
                "Condition": [item.condition],
                "Variant": [item.variant],
            },
        )

        skus.append(sku)
        aspect_card_names.append(card.name)
        aspect_card_numbers.append(card.card_number)
        aspect_conditions.append(item.condition)
        aspect_variants.append(item.variant)
        if card.image_url:
            image_urls.append(card.image_url)
        price = float(item.ebay_price)
        if price < min_price:
            min_price = price

    # Always update/replace the inventory item group (idempotent PUT)
    await ebay_client.create_or_replace_inventory_item_group(
        group_key=group_key,
        title=title[:80],
        description=f"All {set_name} cards. Select card name and number from the variation dropdown.",
        sku_list=skus,
        image_urls=image_urls,
        aspects={
            "Card Name": list(dict.fromkeys(aspect_card_names)),
            "Card Number": list(dict.fromkeys(aspect_card_numbers)),
            "Condition": list(dict.fromkeys(aspect_conditions)),
            "Variant": list(dict.fromkeys(aspect_variants)),
        },
    )

    now = datetime.now(timezone.utc)

    if existing_offer_id:
        # Already listed — update qty/price for each SKU, no new offer or publish needed
        for item in items:
            sku = _make_sku(item.card, item)
            await ebay_client.update_quantity(
                sku=sku,
                offer_id=existing_offer_id,
                new_quantity=item.quantity,
                price=float(item.ebay_price),
            )
            item.ebay_inventory_sku = sku
            item.staged = False
            item.updated_at = now
        db.commit()
        return {"status": "updated", "group_key": group_key, "offer_id": existing_offer_id, "cards_updated": len(items)}
    else:
        # New listing — create offer and publish
        offer_resp = await ebay_client.create_offer_for_group(
            group_key=group_key,
            price=min_price if min_price != float("inf") else 0.99,
        )
        offer_id = offer_resp.get("offerId")
        if not offer_id:
            raise HTTPException(status_code=500, detail=f"eBay group offer creation failed: {offer_resp}")
        await ebay_client.publish_offer(offer_id)

        for item in items:
            item.ebay_inventory_sku = _make_sku(item.card, item)
            item.ebay_group_key = group_key
            item.ebay_group_offer_id = offer_id
            item.listed_on_ebay = True
            item.staged = False
            item.updated_at = now
        db.commit()
        return {"status": "listed", "group_key": group_key, "offer_id": offer_id, "cards_listed": len(items)}


@router.post("/delist-set/{game}/{set_id}")
async def delist_set_from_ebay(game: str, set_id: str, db: Session = Depends(get_db)):
    """Withdraw the multi-variation eBay listing for an entire set."""
    items = db.scalars(
        select(InventoryItem)
        .join(Card)
        .where(Card.game == game, Card.set_id == set_id)
        .where(InventoryItem.ebay_group_offer_id.is_not(None))
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="No group-listed items found for this set")

    # Withdraw the offer (only need to do it once)
    offer_id = items[0].ebay_group_offer_id
    await ebay_client.delist_offer(offer_id)

    now = datetime.now(timezone.utc)
    for item in items:
        item.listed_on_ebay = False
        item.ebay_group_key = None
        item.ebay_group_offer_id = None
        item.updated_at = now
    db.commit()
    return {"status": "delisted", "items_affected": len(items)}


@router.post("/orders/sync")
async def sync_ebay_orders(db: Session = Depends(get_db)):
    """Manually trigger an eBay order poll and process new sales."""
    from app.sync.engine import process_ebay_orders
    processed = await process_ebay_orders(db)
    return {"processed": processed}
