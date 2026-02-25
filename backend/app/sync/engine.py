"""
eBay order sync engine.

on_sale(platform, order_data, db):
  1. Identify inventory_item from eBay SKU
  2. Decrement quantity
  3. Record Order
  4. Delist from eBay if qty hits 0
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.inventory import InventoryItem
from app.models.order import Order

logger = logging.getLogger(__name__)


def _find_item_by_ebay(db: Session, sku: str) -> InventoryItem | None:
    return db.scalar(
        select(InventoryItem).options(joinedload(InventoryItem.card))
        .where(InventoryItem.ebay_inventory_sku == sku)
    )


async def on_sale(platform: str, order_data: dict, db: Session) -> bool:
    """
    Process a single eBay sale event.
    Returns True if handled, False if inventory item not found.

    eBay order structure (relevant fields):
      {"orderId": str, "lineItems": [{"sku": str, "quantity": int, "lineItemCost": {"value": str}}]}
    """
    from app.integrations import ebay as ebay_client

    order_id = str(order_data.get("orderId", order_data.get("order_id", "")))

    # Dedup: skip if already recorded
    existing = db.scalar(select(Order).where(Order.external_order_id == order_id, Order.platform == platform))
    if existing:
        return False

    line_items = order_data.get("lineItems", order_data.get("lineItem", []))
    if not isinstance(line_items, list):
        line_items = [line_items]

    handled = False
    for line in line_items:
        qty_sold = int(line.get("quantity", 1))
        sku = line.get("sku", line.get("inventoryItemSku"))
        item = _find_item_by_ebay(db, sku) if sku else None
        cost = line.get("lineItemCost", {})
        sale_price = Decimal(str(cost.get("value", 0)))

        if not item:
            logger.warning("No inventory item found for %s order %s line %s", platform, order_id, line)
            continue

        # Decrement quantity
        new_qty = max(0, item.quantity - qty_sold)
        item.quantity = new_qty
        item.updated_at = datetime.now(timezone.utc)

        # Record order
        db.add(Order(
            platform=platform,
            external_order_id=order_id,
            inventory_item_id=item.id,
            quantity_sold=qty_sold,
            sale_price=sale_price,
            sold_at=datetime.now(timezone.utc),
        ))

        # Delist from eBay if qty hits 0
        if new_qty == 0 and item.listed_on_ebay and item.ebay_offer_id:
            try:
                await ebay_client.delist_offer(item.ebay_offer_id)
                item.listed_on_ebay = False
            except Exception as e:
                logger.error("Failed to delist eBay offer after sale: %s", e)

        db.commit()
        logger.info("Processed %s sale order %s: item %d qty %d→%d", platform, order_id, item.id, item.quantity + qty_sold, new_qty)
        handled = True

    return handled


async def process_ebay_orders(db: Session) -> int:
    """Poll eBay for recent orders and process new ones. Returns count processed."""
    from app.integrations import ebay as ebay_client
    try:
        orders = await ebay_client.get_orders()
    except Exception as e:
        logger.error("eBay order poll failed: %s", e)
        return 0

    count = 0
    for order in orders:
        if await on_sale("ebay", order, db):
            count += 1
    return count
