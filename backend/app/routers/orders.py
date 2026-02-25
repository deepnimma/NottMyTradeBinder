from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.models.order import Order
from app.schemas.order import OrderOut

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    platform: str | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(Order).order_by(Order.synced_at.desc()).offset(skip).limit(limit)
    if platform:
        stmt = stmt.where(Order.platform == platform)
    return db.scalars(stmt).all()
