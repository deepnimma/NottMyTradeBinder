import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from app.database import get_db
from app.models.card import Card
from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

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


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalize_game(product_line: str) -> str:
    return re.sub(r"\s+", "_", product_line.strip().lower())


@router.post("/import/tcgplayer-csv")
async def import_tcgplayer_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    created = updated = skipped = 0

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

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


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
