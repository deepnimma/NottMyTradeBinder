from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(16))  # "tcgplayer" | "ebay"
    external_order_id: Mapped[str] = mapped_column(String(128), unique=True)
    inventory_item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inventory_items.id"), nullable=True
    )
    quantity_sold: Mapped[int] = mapped_column(Integer, default=1)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    inventory_item: Mapped["InventoryItem | None"] = relationship(back_populates="orders")
