from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/tradebinder.db"

    # eBay (production)
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_redirect_uri: str = ""  # RuName — only needed for OAuth flow
    ebay_refresh_token: str = ""  # paste token from developer portal to skip OAuth
    ebay_sandbox: bool = False

    # eBay listing policies (production)
    # Find these at: ebay.com → Account → Site Preferences → Shipping/Payment/Return policies
    ebay_fulfillment_policy_id: str = ""
    ebay_payment_policy_id: str = ""
    ebay_return_policy_id: str = ""

    # eBay (sandbox) — used when ebay_sandbox=true
    ebay_sandbox_client_id: str = ""
    ebay_sandbox_client_secret: str = ""
    ebay_sandbox_redirect_uri: str = ""
    ebay_sandbox_refresh_token: str = ""

    # eBay listing policies (sandbox)
    ebay_sandbox_fulfillment_policy_id: str = ""
    ebay_sandbox_payment_policy_id: str = ""
    ebay_sandbox_return_policy_id: str = ""

    @property
    def ebay_active_client_id(self) -> str:
        return self.ebay_sandbox_client_id if self.ebay_sandbox else self.ebay_client_id

    @property
    def ebay_active_client_secret(self) -> str:
        return self.ebay_sandbox_client_secret if self.ebay_sandbox else self.ebay_client_secret

    @property
    def ebay_active_redirect_uri(self) -> str:
        return self.ebay_sandbox_redirect_uri if self.ebay_sandbox else self.ebay_redirect_uri

    @property
    def ebay_active_refresh_token(self) -> str:
        return self.ebay_sandbox_refresh_token if self.ebay_sandbox else self.ebay_refresh_token

    @property
    def ebay_active_policy_ids(self) -> dict[str, str]:
        if self.ebay_sandbox:
            return {
                "fulfillmentPolicyId": self.ebay_sandbox_fulfillment_policy_id,
                "paymentPolicyId": self.ebay_sandbox_payment_policy_id,
                "returnPolicyId": self.ebay_sandbox_return_policy_id,
            }
        return {
            "fulfillmentPolicyId": self.ebay_fulfillment_policy_id,
            "paymentPolicyId": self.ebay_payment_policy_id,
            "returnPolicyId": self.ebay_return_policy_id,
        }

    # App
    sync_interval_minutes: int = 5
    app_base_url: str = "http://localhost:8000"  # used for eBay OAuth callback


settings = Settings()
