"""
Populates the local cards table from tcgtracking.com.
Call sync_game_sets() to load all sets for a game into the DB.
Call sync_set_cards() to load all cards for a specific set.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.card_data.tcgtracking import get_sets, get_cards_in_set
from app.models.card import Card

logger = logging.getLogger(__name__)


async def sync_set_cards(game: str, set_id: str | int, set_name: str, db: Session) -> int:
    """
    Fetch cards for a set from API and upsert into DB.
    Returns count of cards upserted.
    """
    products = await get_cards_in_set(game, set_id)
    count = 0
    for p in products:
        # Use the card number if present, otherwise fall back to TCGPlayer product ID
        # (always unique within a set). Never use truncated name as key.
        card_number = str(p.get("number") or "").strip() or f"tcg-{p['id']}"
        stmt = (
            sqlite_insert(Card)
            .values(
                game=game,
                name=p["name"],
                set_id=str(set_id),
                set_name=set_name,
                card_number=card_number,
                image_url=p.get("image_url"),
                tcgplayer_product_id=p.get("id"),
            )
            .on_conflict_do_update(
                index_elements=None,
                # Match on the unique constraint columns
                set_={
                    "name": p["name"],
                    "image_url": p.get("image_url"),
                    "tcgplayer_product_id": p.get("id"),
                },
            )
        )
        # Use the unique constraint manually: check-then-insert/update
        existing = db.scalar(
            select(Card).where(
                Card.game == game,
                Card.set_id == str(set_id),
                Card.card_number == card_number,
            )
        )
        if existing:
            existing.name = p["name"]
            existing.image_url = p.get("image_url")
            existing.tcgplayer_product_id = p.get("id")
        else:
            db.add(Card(
                game=game,
                name=p["name"],
                set_id=str(set_id),
                set_name=set_name,
                card_number=card_number,
                image_url=p.get("image_url"),
                tcgplayer_product_id=p.get("id"),
            ))
        count += 1

    db.commit()
    logger.info("Synced %d cards for %s / %s", count, game, set_name)
    return count


async def sync_game_sets(game: str, db: Session) -> dict:
    """
    Fetch all sets for a game and return their metadata.
    Does NOT load individual cards (too slow for full catalog).
    Returns {"sets": [...], "count": int}
    """
    sets = await get_sets(game)
    logger.info("Found %d sets for %s", len(sets), game)
    return {"sets": sets, "count": len(sets)}
