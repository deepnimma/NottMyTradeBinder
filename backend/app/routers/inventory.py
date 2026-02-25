import csv
import io
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.models.card import Card
from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
logger = logging.getLogger(__name__)

_CONDITION_MAP = {
    "near mint": "NM",
    "near mint foil": "NM",
    "lightly played": "LP",
    "lightly played foil": "LP",
    "moderately played": "MP",
    "moderately played foil": "MP",
    "heavily played": "HP",
    "heavily played foil": "HP",
    "damaged": "D",
    "damaged foil": "D",
}

_CONDITION_REVERSE = {
    "NM": "Near Mint",
    "LP": "Lightly Played",
    "MP": "Moderately Played",
    "HP": "Heavily Played",
    "D": "Damaged",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalize_game(product_line: str) -> str:
    return re.sub(r"\s+", "_", product_line.strip().lower())


def _game_to_title(game: str) -> str:
    return " ".join(w.capitalize() for w in game.replace("_", " ").split())


@router.post("/import/tcgplayer-csv")
async def import_tcgplayer_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    from app.integrations import ebay as ebay_client

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    created = updated = skipped = ebay_updated = 0

    for row in reader:
        try:
            qty = int(row.get("Total Quantity", "0") or "0")
        except ValueError:
            qty = 0
        if qty <= 0:
            skipped += 1
            continue

        tcg_id_raw = row.get("TCGplayer Id", "").strip()
        tcg_product_id = int(tcg_id_raw) if tcg_id_raw.isdigit() else None
        game = _normalize_game(row.get("Product Line", "unknown"))
        set_name = row.get("Set Name", "").strip()
        set_id = _slugify(set_name) if set_name else "unknown"
        card_number = row.get("Number", "").strip() or "0"
        card_name = row.get("Product Name", "").strip()
        condition_raw = row.get("Condition", "Near Mint").strip()
        condition = _CONDITION_MAP.get(condition_raw.lower(), "NM")
        price_raw = row.get("TCG Marketplace Price", "").strip()
        try:
            price = Decimal(price_raw) if price_raw else None
        except InvalidOperation:
            price = None

        # Look up card
        card: Card | None = None
        if tcg_product_id is not None:
            card = db.scalar(
                select(Card).where(Card.tcgplayer_product_id == tcg_product_id)
            )
        if card is None:
            card = db.scalar(
                select(Card).where(
                    Card.game == game,
                    Card.set_id == set_id,
                    Card.card_number == card_number,
                )
            )
        if card is None:
            card = Card(
                game=game,
                name=card_name,
                set_id=set_id,
                set_name=set_name,
                card_number=card_number,
                tcgplayer_product_id=tcg_product_id,
            )
            db.add(card)
            db.flush()  # get card.id

        # Look up inventory item
        item: InventoryItem | None = db.scalar(
            select(InventoryItem).where(
                InventoryItem.card_id == card.id,
                InventoryItem.condition == condition,
            )
        )
        if item is None:
            item = InventoryItem(
                card_id=card.id,
                condition=condition,
                quantity=qty,
                tcgplayer_price=price,
            )
            db.add(item)
            created += 1
        else:
            item.quantity = qty
            if price is not None:
                item.tcgplayer_price = price
            item.updated_at = datetime.now(timezone.utc)
            updated += 1

            # Push updated qty/price to eBay if already listed
            if item.listed_on_ebay and item.ebay_inventory_sku and item.ebay_offer_id:
                try:
                    await ebay_client.update_quantity(
                        sku=item.ebay_inventory_sku,
                        offer_id=item.ebay_offer_id,
                        new_quantity=qty,
                        price=float(price or item.ebay_price or 0),
                    )
                    ebay_updated += 1
                except Exception as e:
                    logger.warning("eBay update failed for item (card %s): %s", card.name, e)

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "ebay_updated": ebay_updated}


@router.get("/export/tcgplayer-csv")
def export_tcgplayer_csv(db: Session = Depends(get_db)):
    items = db.scalars(
        select(InventoryItem).options(joinedload(InventoryItem.card))
    ).all()

    headers = [
        "TCGplayer Id", "Product Line", "Set Name", "Product Name", "Title", "Number", "Rarity",
        "Condition", "TCG Market Price", "TCG Direct Low", "TCG Low Price With Shipping",
        "TCG Low Price", "Total Quantity", "Add to Quantity", "TCG Marketplace Price", "Photo URL",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    for item in items:
        card = item.card
        writer.writerow({
            "TCGplayer Id": card.tcgplayer_product_id or "",
            "Product Line": _game_to_title(card.game),
            "Set Name": card.set_name,
            "Product Name": card.name,
            "Title": "",
            "Number": card.card_number,
            "Rarity": "",
            "Condition": _CONDITION_REVERSE.get(item.condition, item.condition),
            "TCG Market Price": "",
            "TCG Direct Low": "",
            "TCG Low Price With Shipping": "",
            "TCG Low Price": "",
            "Total Quantity": item.quantity,
            "Add to Quantity": 0,
            "TCG Marketplace Price": str(item.tcgplayer_price) if item.tcgplayer_price else "",
            "Photo URL": card.image_url or "",
        })

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tradebinder_export.csv"'},
    )


@router.get("", response_model=list[InventoryItemOut])
def list_inventory(
    skip: int = 0,
    limit: int = 100,
    game: str | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = (
        select(InventoryItem)
        .options(joinedload(InventoryItem.card))
        .offset(skip)
        .limit(limit)
        .order_by(InventoryItem.updated_at.desc())
    )
    if game:
        from app.models.card import Card
        stmt = stmt.join(Card).where(Card.game == game)
    return db.scalars(stmt).all()


@router.post("", response_model=InventoryItemOut, status_code=201)
def create_inventory_item(body: InventoryItemCreate, db: Session = Depends(get_db)):
    item = InventoryItem(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    # Eager-load card for response
    db.expire(item)
    item = db.scalar(
        select(InventoryItem).options(joinedload(InventoryItem.card)).where(InventoryItem.id == item.id)
    )
    return item


@router.post("/bulk", response_model=list[InventoryItemOut], status_code=201)
def bulk_create_inventory_items(body: list[InventoryItemCreate], db: Session = Depends(get_db)):
    """Create or update multiple inventory items at once (upsert by card_id + condition + variant)."""
    result_ids: list[int] = []
    for data in body:
        item = db.scalar(
            select(InventoryItem).where(
                InventoryItem.card_id == data.card_id,
                InventoryItem.condition == data.condition,
                InventoryItem.variant == data.variant,
            )
        )
        if item is None:
            item = InventoryItem(**data.model_dump())
            db.add(item)
            db.flush()
        else:
            item.quantity = data.quantity
            if data.ebay_price is not None:
                item.ebay_price = data.ebay_price
            if data.tcgplayer_price is not None:
                item.tcgplayer_price = data.tcgplayer_price
            if data.notes is not None:
                item.notes = data.notes
            item.updated_at = datetime.now(timezone.utc)
        result_ids.append(item.id)
    db.commit()
    items = db.scalars(
        select(InventoryItem)
        .options(joinedload(InventoryItem.card))
        .where(InventoryItem.id.in_(result_ids))
    ).all()
    return items


@router.get("/{item_id}", response_model=InventoryItemOut)
def get_inventory_item(item_id: int, db: Session = Depends(get_db)):
    item = db.scalar(
        select(InventoryItem).options(joinedload(InventoryItem.card)).where(InventoryItem.id == item_id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=InventoryItemOut)
def update_inventory_item(item_id: int, body: InventoryItemUpdate, db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.expire(item)
    item = db.scalar(
        select(InventoryItem).options(joinedload(InventoryItem.card)).where(InventoryItem.id == item_id)
    )
    return item


@router.delete("/{item_id}", status_code=204)
def delete_inventory_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
