from pathlib import Path

import yaml

_ROOT = Path(__file__).parents[3]  # project root (3 levels up from app/)


def _load() -> dict:
    path = _ROOT / "config.yaml"
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f) or {}


_config = _load()


def get_ebay_policy_ids() -> dict[str, str]:
    ebay = _config.get("ebay", {})
    return {
        "fulfillmentPolicyId": ebay.get("fulfillment_policy_id", ""),
        "paymentPolicyId": ebay.get("payment_policy_id", ""),
        "returnPolicyId": ebay.get("return_policy_id", ""),
    }
