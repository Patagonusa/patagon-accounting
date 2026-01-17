"""
Configuration settings for Patagon Accounting QuickBooks Integration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "Patagon Accounting"
    debug: bool = False
    secret_key: str = "change-this-in-production"

    # QuickBooks OAuth settings
    quickbooks_client_id: str = ""
    quickbooks_client_secret: str = ""
    quickbooks_redirect_uri: str = "http://localhost:8000/callback"
    quickbooks_environment: str = "sandbox"  # sandbox or production

    # QuickBooks API URLs
    quickbooks_auth_url: str = "https://appcenter.intuit.com/connect/oauth2"
    quickbooks_token_url: str = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    quickbooks_sandbox_api: str = "https://sandbox-quickbooks.api.intuit.com"
    quickbooks_production_api: str = "https://quickbooks.api.intuit.com"

    # Storage for tokens (in production, use database)
    quickbooks_access_token: str = ""
    quickbooks_refresh_token: str = ""
    quickbooks_realm_id: str = ""

    @property
    def quickbooks_api_base(self) -> str:
        """Get the appropriate API base URL based on environment."""
        if self.quickbooks_environment == "production":
            return self.quickbooks_production_api
        return self.quickbooks_sandbox_api

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
