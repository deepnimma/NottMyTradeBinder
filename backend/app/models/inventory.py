from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id"), nullable=False)
    condition: Mapped[str] = mapped_column(String(8), default="NM")
    quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Per-platform pricing
    tcgplayer_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    ebay_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Platform listing identifiers
    ebay_inventory_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ebay_offer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Card variant (Normal, Reverse Holo, Holo, First Edition, Promo)
    variant: Mapped[str] = mapped_column(String(32), default="Normal")

    # Listing status
    listed_on_ebay: Mapped[bool] = mapped_column(Boolean, default=False)
    listed_on_tcgplayer: Mapped[bool] = mapped_column(Boolean, default=False)
    staged: Mapped[bool] = mapped_column(Boolean, default=False)  # local changes not yet pushed to eBay

    # eBay multi-variation group listing (per-set listing)
    ebay_group_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ebay_group_offer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    card: Mapped["Card"] = relationship(back_populates="inventory_items")
    orders: Mapped[list["Order"]] = relationship(back_populates="inventory_item")
