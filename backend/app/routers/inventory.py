from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


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
