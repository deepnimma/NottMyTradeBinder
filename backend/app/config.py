from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/tradebinder.db"

    # eBay
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_redirect_uri: str = ""  # RuName from eBay developer portal
    ebay_sandbox: bool = False

    # App
    sync_interval_minutes: int = 5
    app_base_url: str = "http://localhost:8000"  # used for eBay OAuth callback


settings = Settings()
