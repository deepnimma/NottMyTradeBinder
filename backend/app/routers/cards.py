from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, HTTPException

from app.database import get_db
from app.models.card import Card
from app.schemas.card import CardOut, SetOut
from app.card_data.tcgtracking import get_sets as api_get_sets
from app.card_data.sync import sync_set_cards

router = APIRouter(prefix="/api/cards", tags=["cards"])

GAME_ALIASES = {
    "pokemon": "pokemon",
    "weiss_schwarz": "weiss_schwarz",
    "weiss": "weiss_schwarz",
    "ws": "weiss_schwarz",
}


def _normalize_game(game: str) -> str:
    return GAME_ALIASES.get(game.lower(), game.lower())


# ── Set endpoints ─────────────────────────────────────────────────────────────

@router.get("/sets", response_model=list[SetOut])
async def get_sets(game: str = Query(...)):
    """
    Returns all sets for a game directly from TCGTracking API.
    Used to populate the Set dropdown in the frontend.
    """
    game = _normalize_game(game)
    raw_sets = await api_get_sets(game)
    return [
        SetOut(
            set_id=str(s["id"]),
            set_name=s["name"],
            game=game,
            card_count=s.get("product_count", 0),
        )
        for s in raw_sets
    ]


# ── Card endpoints ─────────────────────────────────────────────────────────────

@router.get("/by-set", response_model=list[CardOut])
async def get_cards_by_set(
    set_id: str = Query(...),
    game: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Returns cards for a set. Loads from DB cache if available,
    otherwise fetches from API and caches.
    """
    game = _normalize_game(game)

    # Check DB cache first
    cached = db.scalars(
        select(Card)
        .where(Card.set_id == set_id, Card.game == game)
        .order_by(Card.card_number, Card.name)
    ).all()

    if cached:
        return cached

    # Fetch set name from API for the cache entry
    raw_sets = await api_get_sets(game)
    set_info = next((s for s in raw_sets if str(s["id"]) == str(set_id)), None)
    if not set_info:
        raise HTTPException(status_code=404, detail=f"Set {set_id} not found for game {game}")

    await sync_set_cards(game, set_id, set_info["name"], db)

    return db.scalars(
        select(Card)
        .where(Card.set_id == set_id, Card.game == game)
        .order_by(Card.card_number, Card.name)
    ).all()


@router.get("/search", response_model=list[CardOut])
def search_cards(
    q: str = Query(..., min_length=2),
    game: str | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(Card).where(Card.name.ilike(f"%{q}%"))
    if game:
        stmt = stmt.where(Card.game == _normalize_game(game))
    return db.scalars(stmt.limit(50)).all()


@router.post("/sync-set", status_code=200)
async def sync_set(
    set_id: str = Query(...),
    game: str = Query(...),
    db: Session = Depends(get_db),
):
    """Force-sync a set's cards from TCGTracking API into the local DB."""
    game = _normalize_game(game)
    raw_sets = await api_get_sets(game)
    set_info = next((s for s in raw_sets if str(s["id"]) == str(set_id)), None)
    if not set_info:
        raise HTTPException(status_code=404, detail=f"Set {set_id} not found for game {game}")
    count = await sync_set_cards(game, set_id, set_info["name"], db)
    return {"synced": count, "set_id": set_id, "set_name": set_info["name"]}
