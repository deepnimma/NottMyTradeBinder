from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class OrderOut(BaseModel):
    id: int
    platform: str
    external_order_id: str
    inventory_item_id: int | None
    quantity_sold: int
    sale_price: Decimal | None
    sold_at: datetime | None
    synced_at: datetime

    model_config = {"from_attributes": True}
