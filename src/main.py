"""
Patagon Accounting - QuickBooks Integration

FastAPI application for QuickBooks Online accounting integration.
"""

import secrets
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import get_settings
from src.connectors.quickbooks import QuickBooksConnector
from src.api.routes import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connector instance
qb_connector: QuickBooksConnector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global qb_connector
    try:
        settings = get_settings()
        logger.info(f"Settings loaded, environment: {settings.quickbooks_environment}")
        qb_connector = QuickBooksConnector(settings)
        logger.info("Patagon Accounting started")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
    yield
    logger.info("Patagon Accounting shutting down")


app = FastAPI(
    title="Patagon Accounting",
    description="QuickBooks Online Integration for Patagon Consulting",
    version="1.0.0",
    lifespan=lifespan,
)

# Templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy", "service": "patagon-accounting"}


# Legal pages
@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Privacy Policy page."""
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/eula", response_class=HTMLResponse)
async def eula(request: Request):
    """End-User License Agreement page."""
    return templates.TemplateResponse("eula.html", {"request": request})


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    """Terms of Service (redirects to EULA)."""
    return templates.TemplateResponse("eula.html", {"request": request})


@app.get("/contractors", response_class=HTMLResponse)
async def contractors_page(request: Request):
    """Contractors management page."""
    return templates.TemplateResponse("contractors.html", {"request": request})


def get_quickbooks() -> QuickBooksConnector:
    """Get the QuickBooks connector instance."""
    return qb_connector


# ==================== OAuth Routes ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with QuickBooks connection status."""
    is_connected = qb_connector.is_authenticated if qb_connector else False
    company_name = None

    if is_connected:
        try:
            company_info = await qb_connector.get_company_info()
            company_name = company_info.get("CompanyInfo", {}).get("CompanyName", "Unknown")
        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            is_connected = False

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "is_connected": is_connected,
            "company_name": company_name,
            "realm_id": qb_connector.realm_id if qb_connector else None,
        }
    )


@app.get("/connect")
async def connect_quickbooks():
    """Initiate OAuth connection to QuickBooks."""
    if not qb_connector:
        raise HTTPException(status_code=500, detail="QuickBooks connector not initialized")

    state = secrets.token_urlsafe(16)
    auth_url = qb_connector.get_authorization_url(state=state)

    logger.info("Redirecting to QuickBooks for authorization")
    return RedirectResponse(url=auth_url)


@app.get("/callback")
async def oauth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    realmId: str = None,
    error: str = None,
):
    """Handle OAuth callback from QuickBooks."""
    if error:
        logger.error(f"OAuth error: {error}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"QuickBooks authorization failed: {error}"}
        )

    if not code or not realmId:
        logger.error(f"Missing OAuth parameters: code={bool(code)}, realmId={bool(realmId)}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Missing authorization code or realm ID"}
        )

    try:
        await qb_connector.exchange_code_for_tokens(code, realmId)
        logger.info(f"Successfully connected to QuickBooks, realm_id={realmId}")
        return RedirectResponse(url="/")
    except Exception as e:
        logger.error(f"Failed to exchange tokens: {e}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Failed to connect: {str(e)}"}
        )


@app.get("/disconnect")
async def disconnect_quickbooks():
    """Disconnect from QuickBooks."""
    if qb_connector:
        qb_connector.disconnect()
    return RedirectResponse(url="/")


# ==================== Dashboard Routes ====================

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request):
    """Customers page."""
    if not qb_connector or not qb_connector.is_authenticated:
        return RedirectResponse(url="/")

    return templates.TemplateResponse("customers.html", {"request": request})


@app.get("/invoices", response_class=HTMLResponse)
async def invoices_page(request: Request):
    """Invoices page."""
    if not qb_connector or not qb_connector.is_authenticated:
        return RedirectResponse(url="/")

    return templates.TemplateResponse("invoices.html", {"request": request})


@app.get("/payments", response_class=HTMLResponse)
async def payments_page(request: Request):
    """Payments page."""
    if not qb_connector or not qb_connector.is_authenticated:
        return RedirectResponse(url="/")

    return templates.TemplateResponse("payments.html", {"request": request})


@app.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request):
    """Chart of Accounts page."""
    if not qb_connector or not qb_connector.is_authenticated:
        return RedirectResponse(url="/")

    return templates.TemplateResponse("accounts.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
