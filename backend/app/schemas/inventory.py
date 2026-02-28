from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from app.schemas.card import CardOut


class InventoryItemCreate(BaseModel):
    card_id: int
    condition: str = "NM"
    variant: str = "Normal"
    quantity: int
    tcgplayer_price: Decimal | None = None
    ebay_price: Decimal | None = None
    notes: str | None = None


class InventoryItemUpdate(BaseModel):
    condition: str | None = None
    variant: str | None = None
    quantity: int | None = None
    tcgplayer_price: Decimal | None = None
    ebay_price: Decimal | None = None
    notes: str | None = None


class InventoryItemOut(BaseModel):
    id: int
    card: CardOut
    condition: str
    variant: str
    quantity: int
    tcgplayer_price: Decimal | None
    ebay_price: Decimal | None
    ebay_inventory_sku: str | None
    ebay_offer_id: str | None
    ebay_group_key: str | None
    ebay_group_offer_id: str | None
    listed_on_ebay: bool
    listed_on_tcgplayer: bool
    staged: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
