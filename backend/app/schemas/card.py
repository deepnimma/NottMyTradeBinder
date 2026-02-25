from pydantic import BaseModel


class CardOut(BaseModel):
    id: int
    game: str
    name: str
    set_id: str
    set_name: str
    card_number: str
    image_url: str | None
    tcgplayer_product_id: int | None

    model_config = {"from_attributes": True}


class SetOut(BaseModel):
    set_id: str
    set_name: str
    game: str
    card_count: int
