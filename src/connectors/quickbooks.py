"""
QuickBooks Online API Connector

Handles OAuth 2.0 authentication and API calls to QuickBooks Online.
"""

import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path

import httpx

from src.config import Settings

logger = logging.getLogger(__name__)

# Token storage file (in production, use database)
TOKEN_FILE = Path(__file__).parent.parent.parent / "quickbooks_tokens.json"


class QuickBooksError(Exception):
    """Base exception for QuickBooks operations."""
    pass


class QuickBooksConnector:
    """Connector for QuickBooks Online API."""

    SCOPES = "com.intuit.quickbooks.accounting"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client_id = settings.quickbooks_client_id
        self.client_secret = settings.quickbooks_client_secret
        self.redirect_uri = settings.quickbooks_redirect_uri
        self.environment = settings.quickbooks_environment

        # Token storage
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.realm_id: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Load stored tokens
        self._load_tokens()

    @property
    def api_base_url(self) -> str:
        """Get API base URL based on environment."""
        if self.environment == "production":
            return "https://quickbooks.api.intuit.com"
        return "https://sandbox-quickbooks.api.intuit.com"

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid tokens."""
        return bool(self.access_token and self.realm_id)

    @property
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expiry:
            return True
        return datetime.utcnow() >= self.token_expiry

    def get_authorization_url(self, state: str = "security_token") -> str:
        """
        Generate the OAuth 2.0 authorization URL.

        Args:
            state: Random state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "scope": self.SCOPES,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.settings.quickbooks_auth_url}?{query_string}"

    async def exchange_code_for_tokens(self, auth_code: str, realm_id: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            auth_code: Authorization code from OAuth callback
            realm_id: QuickBooks company ID (realmId)

        Returns:
            Token response dict
        """
        # Create Basic auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.quickbooks_token_url,
                headers=headers,
                data=data,
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to exchange code for tokens",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise QuickBooksError(f"Token exchange failed: {response.text}")

            token_data = response.json()

        # Store tokens
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        self.realm_id = realm_id
        expires_in = token_data.get("expires_in", 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

        # Persist tokens
        self._save_tokens()

        logger.info(
            "Successfully obtained QuickBooks tokens",
            realm_id=realm_id,
            expires_in=expires_in,
        )

        return token_data

    async def refresh_access_token(self) -> dict:
        """
        Refresh the access token using the refresh token.

        Returns:
            Token response dict
        """
        if not self.refresh_token:
            raise QuickBooksError("No refresh token available")

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.quickbooks_token_url,
                headers=headers,
                data=data,
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to refresh token",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise QuickBooksError(f"Token refresh failed: {response.text}")

            token_data = response.json()

        # Update tokens
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        expires_in = token_data.get("expires_in", 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

        # Persist tokens
        self._save_tokens()

        logger.info("Successfully refreshed QuickBooks access token")

        return token_data

    async def _ensure_valid_token(self):
        """Ensure we have a valid access token, refreshing if needed."""
        if self.is_token_expired and self.refresh_token:
            await self.refresh_access_token()

    async def api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """
        Make an authenticated API request to QuickBooks.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /v3/company/{realmId}/customer)
            data: Request body for POST/PUT
            params: Query parameters

        Returns:
            API response as dict
        """
        await self._ensure_valid_token()

        if not self.access_token or not self.realm_id:
            raise QuickBooksError("Not authenticated. Please connect to QuickBooks first.")

        url = f"{self.api_base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
            )

            if response.status_code == 401:
                # Token might be expired, try refresh
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                )

            if response.status_code >= 400:
                logger.error(
                    "QuickBooks API error",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise QuickBooksError(f"API error: {response.status_code} - {response.text}")

            return response.json()

    # ==================== Company Info ====================

    async def get_company_info(self) -> dict:
        """Get company information."""
        endpoint = f"/v3/company/{self.realm_id}/companyinfo/{self.realm_id}"
        return await self.api_request("GET", endpoint)

    # ==================== Customers ====================

    async def get_customers(self, max_results: int = 100) -> list:
        """Get all customers."""
        endpoint = f"/v3/company/{self.realm_id}/query"
        params = {"query": f"SELECT * FROM Customer MAXRESULTS {max_results}"}
        response = await self.api_request("GET", endpoint, params=params)
        return response.get("QueryResponse", {}).get("Customer", [])

    async def get_customer(self, customer_id: str) -> dict:
        """Get a specific customer."""
        endpoint = f"/v3/company/{self.realm_id}/customer/{customer_id}"
        response = await self.api_request("GET", endpoint)
        return response.get("Customer", {})

    async def create_customer(self, customer_data: dict) -> dict:
        """Create a new customer."""
        endpoint = f"/v3/company/{self.realm_id}/customer"
        response = await self.api_request("POST", endpoint, data=customer_data)
        return response.get("Customer", {})

    # ==================== Invoices ====================

    async def get_invoices(self, max_results: int = 100) -> list:
        """Get all invoices."""
        endpoint = f"/v3/company/{self.realm_id}/query"
        params = {"query": f"SELECT * FROM Invoice MAXRESULTS {max_results}"}
        response = await self.api_request("GET", endpoint, params=params)
        return response.get("QueryResponse", {}).get("Invoice", [])

    async def get_invoice(self, invoice_id: str) -> dict:
        """Get a specific invoice."""
        endpoint = f"/v3/company/{self.realm_id}/invoice/{invoice_id}"
        response = await self.api_request("GET", endpoint)
        return response.get("Invoice", {})

    async def create_invoice(self, invoice_data: dict) -> dict:
        """Create a new invoice."""
        endpoint = f"/v3/company/{self.realm_id}/invoice"
        response = await self.api_request("POST", endpoint, data=invoice_data)
        return response.get("Invoice", {})

    # ==================== Payments ====================

    async def get_payments(self, max_results: int = 100) -> list:
        """Get all payments."""
        endpoint = f"/v3/company/{self.realm_id}/query"
        params = {"query": f"SELECT * FROM Payment MAXRESULTS {max_results}"}
        response = await self.api_request("GET", endpoint, params=params)
        return response.get("QueryResponse", {}).get("Payment", [])

    async def create_payment(self, payment_data: dict) -> dict:
        """Create a new payment."""
        endpoint = f"/v3/company/{self.realm_id}/payment"
        response = await self.api_request("POST", endpoint, data=payment_data)
        return response.get("Payment", {})

    # ==================== Chart of Accounts ====================

    async def get_accounts(self, max_results: int = 100) -> list:
        """Get chart of accounts."""
        endpoint = f"/v3/company/{self.realm_id}/query"
        params = {"query": f"SELECT * FROM Account MAXRESULTS {max_results}"}
        response = await self.api_request("GET", endpoint, params=params)
        return response.get("QueryResponse", {}).get("Account", [])

    # ==================== Vendors ====================

    async def get_vendors(self, max_results: int = 100) -> list:
        """Get all vendors."""
        endpoint = f"/v3/company/{self.realm_id}/query"
        params = {"query": f"SELECT * FROM Vendor MAXRESULTS {max_results}"}
        response = await self.api_request("GET", endpoint, params=params)
        return response.get("QueryResponse", {}).get("Vendor", [])

    # ==================== Bills ====================

    async def get_bills(self, max_results: int = 100) -> list:
        """Get all bills."""
        endpoint = f"/v3/company/{self.realm_id}/query"
        params = {"query": f"SELECT * FROM Bill MAXRESULTS {max_results}"}
        response = await self.api_request("GET", endpoint, params=params)
        return response.get("QueryResponse", {}).get("Bill", [])

    # ==================== Token Storage ====================

    def _save_tokens(self):
        """Save tokens to file (in production, use database)."""
        token_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "realm_id": self.realm_id,
            "token_expiry": self.token_expiry.isoformat() if self.token_expiry else None,
        }
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump(token_data, f)
            logger.info("Tokens saved successfully")
        except Exception as e:
            logger.error("Failed to save tokens", error=str(e))

    def _load_tokens(self):
        """Load tokens from file."""
        try:
            if TOKEN_FILE.exists():
                with open(TOKEN_FILE, "r") as f:
                    token_data = json.load(f)
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.realm_id = token_data.get("realm_id")
                expiry_str = token_data.get("token_expiry")
                if expiry_str:
                    self.token_expiry = datetime.fromisoformat(expiry_str)
                logger.info("Tokens loaded successfully", realm_id=self.realm_id)
        except Exception as e:
            logger.warning("Failed to load tokens", error=str(e))

    def disconnect(self):
        """Clear stored tokens."""
        self.access_token = None
        self.refresh_token = None
        self.realm_id = None
        self.token_expiry = None
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        logger.info("Disconnected from QuickBooks")
