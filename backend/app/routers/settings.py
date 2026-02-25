"""
Settings router — returns masked config values and allows live updates
to the .env file (restart required for most changes).
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "****" if len(value) > 4 else "****"


@router.get("")
def get_settings():
    return {
        "tcgplayer_public_key": _mask(settings.tcgplayer_public_key),
        "tcgplayer_store_key": _mask(settings.tcgplayer_store_key),
        "ebay_client_id": _mask(settings.ebay_client_id),
        "ebay_sandbox": settings.ebay_sandbox,
        "sync_interval_minutes": settings.sync_interval_minutes,
        "app_base_url": settings.app_base_url,
    }
