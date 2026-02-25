"""
Client for https://tcgtracking.com/tcgapi/v1
No auth required. Cloudflare CDN-cached (sets/cards: 7 days, pricing: 1 day).

Response shapes discovered from live API:
  GET /v1/categories → {"categories": [{"id": int, "name": str, ...}]}
  GET /v1/{cat}/sets → {"sets": [{"id": int, "name": str, "abbreviation": str, ...}]}
  GET /v1/{cat}/sets/{set_id} → {"set_id", "set_name", "products": [{"id": int, "name": str, "number": str|null, "image_url": str, ...}]}
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://tcgtracking.com/tcgapi/v1"

# Known stable category IDs (verified 2026-02-24)
KNOWN_CATEGORIES: dict[str, int] = {
    "pokemon": 3,
    "weiss_schwarz": 20,
}

_category_cache: dict[str, int] = dict(KNOWN_CATEGORIES)


async def _get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(f"{BASE_URL}{path}")
        resp.raise_for_status()
        return resp.json()


async def get_categories() -> list[dict]:
    data = await _get("/categories")
    return data.get("categories", [])


async def resolve_category_id(game: str) -> int:
    """Resolve a game key to its TCGTracking numeric category ID."""
    game = game.lower().replace(" ", "_")
    if game in _category_cache:
        return _category_cache[game]

    categories = await get_categories()
    hints = game.replace("_", " ").split()
    for cat in categories:
        cat_name = cat.get("name", "").lower()
        if all(h in cat_name for h in hints):
            cat_id = int(cat["id"])
            _category_cache[game] = cat_id
            logger.info("Resolved game '%s' → category %d", game, cat_id)
            return cat_id

    raise ValueError(
        f"Cannot resolve category ID for game '{game}'. "
        f"Available: {[c.get('name') for c in categories]}"
    )


async def get_sets(game: str) -> list[dict]:
    """Return list of set objects for a game."""
    cat_id = await resolve_category_id(game)
    data = await _get(f"/{cat_id}/sets")
    return data.get("sets", [])


async def get_cards_in_set(game: str, set_id: str | int) -> list[dict]:
    """Return list of product/card objects for a set."""
    cat_id = await resolve_category_id(game)
    data = await _get(f"/{cat_id}/sets/{set_id}")
    return data.get("products", [])
