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
from urllib.parse import urlencode

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
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.marketing",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
    "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.finances",
    "https://api.ebay.com/oauth/api_scope/sell.payment.dispute",
    "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.reputation",
    "https://api.ebay.com/oauth/api_scope/sell.reputation.readonly",
    "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription",
    "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.stores",
    "https://api.ebay.com/oauth/api_scope/sell.stores.readonly",
    "https://api.ebay.com/oauth/scope/sell.edelivery",
    "https://api.ebay.com/oauth/api_scope/commerce.vero",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.mapping",
    "https://api.ebay.com/oauth/api_scope/commerce.message",
    "https://api.ebay.com/oauth/api_scope/commerce.feedback",
    "https://api.ebay.com/oauth/api_scope/commerce.shipping",
]

# In-process token store (single-seller app)
_access_token: str | None = None
_refresh_token: str | None = None
_access_expiry: datetime | None = None


def init_tokens_from_env() -> None:
    """Load the user access token from .env and use it directly as the Bearer token."""
    global _access_token, _access_expiry
    token = settings.ebay_active_refresh_token
    if token:
        _access_token = token
        _access_expiry = None  # no expiry tracking; eBay returns 401 when it expires
        logger.info("eBay user token loaded from environment")


def _base() -> str:
    return _BASE[settings.ebay_sandbox]


def _auth_base() -> str:
    return _AUTH_BASE[settings.ebay_sandbox]


def get_auth_url() -> str:
    """Build the eBay OAuth login URL for the seller to authorize the app."""
    if not settings.ebay_active_client_id:
        raise RuntimeError("EBAY_CLIENT_ID not configured")
    params = {
        "client_id": settings.ebay_active_client_id,
        "response_type": "code",
        "redirect_uri": settings.ebay_active_redirect_uri,
        "scope": " ".join(SCOPES),
        "state": "tradebinder",
    }
    return f"{_auth_base()}/oauth2/authorize?{urlencode(params)}"


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
        if not resp.is_success:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f"eBay token refresh failed {resp.status_code}: {detail}")
        data = resp.json()
        _access_token = data["access_token"]
        _access_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in", 7200)))
        logger.info("eBay access token refreshed")


async def _get_token() -> str:
    now = datetime.now(timezone.utc)
    if _access_token:
        # If no expiry set (token from env), use directly; otherwise check expiry
        if _access_expiry is None or now < _access_expiry - timedelta(minutes=5):
            return _access_token
    if _refresh_token:
        await _refresh_access_token()
        return _access_token
    raise RuntimeError("eBay not authenticated. Set EBAY_REFRESH_TOKEN in .env.")


async def _request(method: str, path: str, **kwargs) -> Any:
    token = await _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Language": "en-US",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method, f"{_base()}{path}", headers=headers, **kwargs
        )
        if resp.status_code == 204:
            return {}
        if not resp.is_success:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            logger.error("eBay API %s %s → %s: %s", method.upper(), path, resp.status_code, detail)
            raise RuntimeError(f"eBay API error {resp.status_code}: {detail}")
        return resp.json()


# ── Merchant Location ──────────────────────────────────────────────────────────

async def create_merchant_location(key: str = "home", country: str = "US") -> dict:
    """
    POST /sell/inventory/v1/location/{key}
    phone and postalCode are required by eBay — set in .env:
      EBAY_MERCHANT_LOCATION_PHONE=5551234567
      EBAY_MERCHANT_LOCATION_POSTAL_CODE=10001
    Content-Language header intentionally omitted (location endpoint rejects it).
    """
    phone = settings.ebay_merchant_location_phone
    postal_code = settings.ebay_merchant_location_postal_code
    if not phone or not postal_code:
        raise RuntimeError(
            "Cannot auto-create eBay merchant location: "
            "EBAY_MERCHANT_LOCATION_PHONE and EBAY_MERCHANT_LOCATION_POSTAL_CODE "
            "must be set in .env."
        )

    token = await _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "location": {"address": {"country": country, "postalCode": postal_code}},
        "name": "My Warehouse",
        "phone": phone,
        "merchantLocationStatus": "ENABLED",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/sell/inventory/v1/location/{key}",
            headers=headers,
            json=payload,
        )
        if resp.status_code in (200, 204):
            logger.info("eBay merchant location '%s' created", key)
            return resp.json() if resp.content else {}
        if resp.status_code == 409:
            logger.debug("eBay merchant location '%s' already exists", key)
            return {}
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"eBay location create failed {resp.status_code}: {detail}")


async def get_merchant_location_key() -> str:
    """
    Return a valid merchant location key for this account.
    Lists all locations; returns the first ENABLED one.
    Raises RuntimeError with setup instructions if none exist.
    """
    data = await _request("GET", "/sell/inventory/v1/location")
    locations = data.get("locations", [])
    enabled = [loc for loc in locations if loc.get("merchantLocationStatus") == "ENABLED"]
    if enabled:
        key = enabled[0]["merchantLocationKey"]
        logger.debug("Using eBay merchant location key '%s'", key)
        return key
    if locations:
        key = locations[0]["merchantLocationKey"]
        logger.warning("No ENABLED eBay location found; using '%s'", key)
        return key
    logger.info("No eBay merchant locations found; creating default location 'home'")
    await create_merchant_location(key="home", country="US")
    return "home"


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
        "variantSKUs": sku_list,
        "variesBy": {
            "specifications": [
                {"name": name, "values": values}
                for name, values in aspects.items()
            ]
        },
    }
    if image_urls:
        payload["imageUrls"] = image_urls[:12]  # eBay supports up to 12 images
    return await _request(
        "PUT", f"/sell/inventory/v1/inventory_item_group/{group_key}", json=payload
    )


def _listing_policies() -> dict:
    """Return only non-empty policy IDs to avoid eBay 500 errors on blank values."""
    raw = settings.ebay_active_policy_ids
    return {k: v for k, v in raw.items() if v}



async def create_offer(
    sku: str,
    price: float,
    merchant_location_key: str = "",
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
        "merchantLocationKey": merchant_location_key or settings.ebay_merchant_location_key,
    }
    policies = _listing_policies()
    if policies:
        payload["listingPolicies"] = policies
    return await _request("POST", "/sell/inventory/v1/offer", json=payload)


async def get_offers_for_sku(sku: str) -> list[dict]:
    """GET /sell/inventory/v1/offer?sku={sku} — list existing offers for a SKU."""
    data = await _request("GET", "/sell/inventory/v1/offer", params={"sku": sku})
    return data.get("offers", [])


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
