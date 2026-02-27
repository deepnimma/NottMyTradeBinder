"""
eBay Selling API client.
Auth: OAuth 2.0 Authorization Code Grant.
  - Scopes: sell.inventory, sell.fulfillment
  - Tokens expire in 2 hours; refresh tokens last 18 months.
  - OAuth flow:
      1. User visits /api/ebay/auth-url to get login URL
      2. eBay redirects to APP_BASE_URL/api/ebay/callback?code=...
      3. App exchanges code for access+refresh tokens
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# eBay API base URLs
_BASE = {
    False: "https://api.ebay.com",
    True: "https://api.sandbox.ebay.com",
}
_AUTH_BASE = {
    False: "https://auth.ebay.com",
    True: "https://auth.sandbox.ebay.com",
}

SCOPES = [
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
]

# In-process token store (single-seller app)
_access_token: str | None = None
_refresh_token: str | None = None
_access_expiry: datetime | None = None


def init_tokens_from_env() -> None:
    """Load refresh token from .env on startup, bypassing the OAuth flow."""
    global _refresh_token
    token = settings.ebay_active_refresh_token
    if token:
        _refresh_token = token
        logger.info("eBay refresh token loaded from environment")


def _base() -> str:
    return _BASE[settings.ebay_sandbox]


def _auth_base() -> str:
    return _AUTH_BASE[settings.ebay_sandbox]


def get_auth_url() -> str:
    """Build the eBay OAuth login URL for the seller to authorize the app."""
    if not settings.ebay_active_client_id:
        raise RuntimeError("EBAY_CLIENT_ID not configured")
    scope_str = " ".join(SCOPES)
    callback = f"{settings.app_base_url}/api/ebay/callback"
    return (
        f"{_auth_base()}/oauth2/authorize"
        f"?client_id={settings.ebay_active_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.ebay_active_redirect_uri}"
        f"&scope={scope_str}"
        f"&state=tradebinder"
    )


async def exchange_code(code: str) -> None:
    """Exchange an authorization code for access + refresh tokens."""
    global _access_token, _refresh_token, _access_expiry
    callback = f"{settings.app_base_url}/api/ebay/callback"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/identity/v1/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.ebay_active_redirect_uri,
            },
            auth=(settings.ebay_active_client_id, settings.ebay_active_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        _access_token = data["access_token"]
        _refresh_token = data.get("refresh_token")
        expires_in = int(data.get("expires_in", 7200))
        _access_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        logger.info("eBay tokens acquired, access expires %s", _access_expiry)


async def _refresh_access_token() -> None:
    global _access_token, _access_expiry
    if not _refresh_token:
        raise RuntimeError("No eBay refresh token available. Complete OAuth flow first.")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/identity/v1/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": _refresh_token,
                "scope": " ".join(SCOPES),
            },
            auth=(settings.ebay_active_client_id, settings.ebay_active_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        _access_token = data["access_token"]
        _access_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in", 7200)))
        logger.info("eBay access token refreshed")


async def _get_token() -> str:
    now = datetime.now(timezone.utc)
    if _access_token and _access_expiry and now < _access_expiry - timedelta(minutes=5):
        return _access_token
    if _refresh_token:
        await _refresh_access_token()
        return _access_token
    raise RuntimeError("eBay not authenticated. Visit /api/ebay/auth-url to connect.")


async def _request(method: str, path: str, **kwargs) -> Any:
    token = await _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method, f"{_base()}{path}", headers=headers, **kwargs
        )
        if resp.status_code == 204:
            return {}
        resp.raise_for_status()
        return resp.json()


# ── Inventory ──────────────────────────────────────────────────────────────────

async def create_or_replace_inventory_item(
    sku: str,
    title: str,
    description: str,
    quantity: int,
    image_url: str | None = None,
    condition: str = "LIKE_NEW",
    aspects: dict[str, list[str]] | None = None,
) -> dict:
    """
    PUT /sell/inventory/v1/inventory_item/{sku}
    eBay condition mappings: NM → LIKE_NEW, LP → VERY_GOOD, MP → GOOD, HP → ACCEPTABLE
    Pass aspects dict when this item is part of a multi-variation group.
    """
    product: dict = {
        "title": title,
        "description": description,
    }
    if image_url:
        product["imageUrls"] = [image_url]
    if aspects:
        product["aspects"] = aspects
    payload: dict = {
        "availability": {"shipToLocationAvailability": {"quantity": quantity}},
        "condition": condition,
        "product": product,
    }
    return await _request("PUT", f"/sell/inventory/v1/inventory_item/{sku}", json=payload)


async def create_or_replace_inventory_item_group(
    group_key: str,
    title: str,
    description: str,
    sku_list: list[str],
    image_urls: list[str],
    aspects: dict[str, list[str]],
) -> dict:
    """
    PUT /sell/inventory/v1/inventory_item_group/{groupKey}
    Creates a multi-variation listing group linking multiple SKUs.
    aspects = {"Card Name": ["Charizard", "Pikachu"], "Card Number": ["001", "002"]}
    """
    payload: dict = {
        "title": title,
        "description": description,
        "aspects": aspects,
        "variantSKUs": sku_list,
    }
    if image_urls:
        payload["imageUrls"] = image_urls[:12]  # eBay supports up to 12 images
    return await _request(
        "PUT", f"/sell/inventory/v1/inventory_item_group/{group_key}", json=payload
    )


async def create_offer_for_group(
    group_key: str,
    price: float,
    marketplace_id: str = "EBAY_US",
    category_id: str = "2536",
) -> dict:
    """POST /sell/inventory/v1/offer — create an offer for a multi-variation group."""
    payload = {
        "inventoryItemGroupKey": group_key,
        "marketplaceId": marketplace_id,
        "format": "FIXED_PRICE",
        "listingDuration": "GTC",
        "pricingSummary": {"price": {"value": str(round(price, 2)), "currency": "USD"}},
        "categoryId": category_id,
        "listingPolicies": settings.ebay_active_policy_ids,
    }
    return await _request("POST", "/sell/inventory/v1/offer", json=payload)


async def create_offer(
    sku: str,
    price: float,
    listing_duration: str = "GTC",  # Good Till Cancelled
    marketplace_id: str = "EBAY_US",
    category_id: str = "2536",  # Trading Card Games category
) -> dict:
    """POST /sell/inventory/v1/offer — create a new offer for an inventory item."""
    payload = {
        "sku": sku,
        "marketplaceId": marketplace_id,
        "format": "FIXED_PRICE",
        "listingDuration": listing_duration,
        "pricingSummary": {"price": {"value": str(round(price, 2)), "currency": "USD"}},
        "categoryId": category_id,
        "listingPolicies": settings.ebay_active_policy_ids,
    }
    return await _request("POST", "/sell/inventory/v1/offer", json=payload)


async def publish_offer(offer_id: str) -> dict:
    """POST /sell/inventory/v1/offer/{offerId}/publish — make offer a live listing."""
    return await _request("POST", f"/sell/inventory/v1/offer/{offer_id}/publish")


async def update_quantity(sku: str, offer_id: str, new_quantity: int, price: float) -> dict:
    """
    POST /sell/inventory/v1/bulk_update_price_quantity
    Updates quantity (and optionally price) for an existing offer.
    """
    payload = {
        "requests": [
            {
                "offers": [
                    {
                        "offerId": offer_id,
                        "price": {"value": str(round(price, 2)), "currency": "USD"},
                    }
                ],
                "shipToLocationAvailability": {"quantity": new_quantity},
                "sku": sku,
            }
        ]
    }
    return await _request("POST", "/sell/inventory/v1/bulk_update_price_quantity", json=payload)


async def delist_offer(offer_id: str) -> dict:
    """POST /sell/inventory/v1/offer/{offerId}/withdraw — end a live listing."""
    return await _request("POST", f"/sell/inventory/v1/offer/{offer_id}/withdraw")


# ── Orders ─────────────────────────────────────────────────────────────────────

async def get_orders(filter_str: str | None = None, limit: int = 50) -> list[dict]:
    """
    GET /sell/fulfillment/v1/order
    filter example: "orderfulfillmentstatus:{NOT_STARTED}"
    Returns list of order objects.
    """
    params: dict = {"limit": limit}
    if filter_str:
        params["filter"] = filter_str
    data = await _request("GET", "/sell/fulfillment/v1/order", params=params)
    return data.get("orders", [])
