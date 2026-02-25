from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("game", "set_id", "card_number", name="uq_card_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game: Mapped[str] = mapped_column(String(32))  # "pokemon" | "weiss_schwarz"
    name: Mapped[str] = mapped_column(String(256))
    set_id: Mapped[str] = mapped_column(String(64))
    set_name: Mapped[str] = mapped_column(String(256))
    card_number: Mapped[str] = mapped_column(String(32))
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tcgplayer_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="card")
