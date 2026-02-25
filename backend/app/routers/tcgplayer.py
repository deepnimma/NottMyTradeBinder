"""
TCGPlayer listing management endpoints.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations import tcgplayer as tcg
from app.models.inventory import InventoryItem

router = APIRouter(prefix="/api/tcgplayer", tags=["tcgplayer"])


@router.post("/list/{item_id}")
async def list_on_tcgplayer(item_id: int, db: Session = Depends(get_db)):
    """Create or update a TCGPlayer SKU for an inventory item."""
    item = db.scalar(select(InventoryItem).where(InventoryItem.id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if not item.card.tcgplayer_product_id:
        raise HTTPException(status_code=400, detail="Card has no TCGPlayer product ID")
    if item.tcgplayer_price is None:
        raise HTTPException(status_code=400, detail="Set tcgplayer_price before listing")

    result = await tcg.create_or_update_sku(
        product_id=item.card.tcgplayer_product_id,
        condition=item.condition,
        quantity=item.quantity,
        price=float(item.tcgplayer_price),
    )
    # Extract the assigned SKU ID from response if present
    skus = result.get("results", [])
    if skus and "skuId" in skus[0]:
        item.tcgplayer_sku_id = skus[0]["skuId"]
    item.listed_on_tcgplayer = True
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "listed", "tcgplayer_response": result}


@router.post("/delist/{item_id}")
async def delist_from_tcgplayer(item_id: int, db: Session = Depends(get_db)):
    """Remove a TCGPlayer listing by setting quantity to 0."""
    item = db.scalar(select(InventoryItem).where(InventoryItem.id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if not item.tcgplayer_sku_id:
        raise HTTPException(status_code=400, detail="No TCGPlayer SKU ID on file")

    result = await tcg.delist_sku(item.tcgplayer_sku_id)
    item.listed_on_tcgplayer = False
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "delisted", "tcgplayer_response": result}


@router.post("/orders/sync")
async def sync_tcgplayer_orders(db: Session = Depends(get_db)):
    """Manually trigger a TCGPlayer order poll and process new sales."""
    from app.sync.engine import process_tcgplayer_orders
    processed = await process_tcgplayer_orders(db)
    return {"processed": processed}
