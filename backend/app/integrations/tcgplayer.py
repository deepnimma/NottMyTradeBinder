"""
TCGPlayer API client.
Auth: POST https://api.tcgplayer.com/token with PUBLIC_KEY + PRIVATE_KEY → bearer token (14-day TTL).
Store-level endpoints require store authorization (storeKey).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tcgplayer.com"

# In-process token cache
_token: str | None = None
_token_expiry: datetime | None = None


async def _get_token() -> str:
    global _token, _token_expiry
    now = datetime.now(timezone.utc)
    if _token and _token_expiry and now < _token_expiry - timedelta(minutes=30):
        return _token

    if not settings.tcgplayer_public_key or not settings.tcgplayer_private_key:
        raise RuntimeError("TCGPlayer API keys not configured. Set TCGPLAYER_PUBLIC_KEY and TCGPLAYER_PRIVATE_KEY in .env")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.tcgplayer_public_key,
                "client_secret": settings.tcgplayer_private_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        _token = data["access_token"]
        expires_in = int(data.get("expires_in", 1209600))  # default 14 days
        _token_expiry = now + timedelta(seconds=expires_in)
        logger.info("TCGPlayer token refreshed, expires %s", _token_expiry)
        return _token


async def _request(method: str, path: str, **kwargs) -> Any:
    token = await _get_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── Inventory ──────────────────────────────────────────────────────────────────

async def create_or_update_sku(
    product_id: int,
    condition: str,
    quantity: int,
    price: float,
) -> dict:
    """
    Add or update a SKU in the store's inventory.
    condition: "NM" maps to conditionId 1 (Near Mint) on TCGPlayer.
    Returns the response from TCGPlayer.
    """
    CONDITION_MAP = {"NM": 1, "LP": 2, "MP": 3, "HP": 4, "D": 5}
    condition_id = CONDITION_MAP.get(condition.upper(), 1)

    store_key = settings.tcgplayer_store_key
    if not store_key:
        raise RuntimeError("TCGPLAYER_STORE_KEY not configured")

    payload = [
        {
            "productId": product_id,
            "conditionId": condition_id,
            "languageId": 1,  # English
            "quantity": quantity,
            "price": float(price),
        }
    ]
    return await _request("PUT", f"/stores/{store_key}/inventory/skus", json=payload)


async def update_sku_quantity(sku_id: int, quantity: int) -> dict:
    """Update inventory quantity for an existing SKU."""
    store_key = settings.tcgplayer_store_key
    payload = [{"skuId": sku_id, "quantity": quantity}]
    return await _request("PUT", f"/stores/{store_key}/inventory/skus/quantity", json=payload)


async def delist_sku(sku_id: int) -> dict:
    """Remove a SKU from store inventory (set qty to 0)."""
    return await update_sku_quantity(sku_id, 0)


# ── Orders ─────────────────────────────────────────────────────────────────────

async def get_orders(offset: int = 0, limit: int = 50, status: str = "Paid") -> list[dict]:
    """
    Poll recent orders. status options: Paid, Shipped, Cancelled, etc.
    Returns list of order objects.
    """
    store_key = settings.tcgplayer_store_key
    data = await _request(
        "GET",
        f"/stores/{store_key}/orders",
        params={"offset": offset, "limit": limit, "status": status},
    )
    # Response shape: {"orders": [...]} or list
    if isinstance(data, list):
        return data
    return data.get("orders", data.get("results", []))
