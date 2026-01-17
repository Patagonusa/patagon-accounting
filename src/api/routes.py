"""
API Routes for Patagon Accounting

REST API endpoints for QuickBooks data.
"""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()


def get_qb_connector():
    """Get QuickBooks connector from main app."""
    from src.main import qb_connector
    if not qb_connector:
        raise HTTPException(status_code=500, detail="QuickBooks connector not initialized")
    if not qb_connector.is_authenticated:
        raise HTTPException(status_code=401, detail="Not connected to QuickBooks")
    return qb_connector


# ==================== Connection Status ====================

@router.get("/status")
async def get_status():
    """Get QuickBooks connection status."""
    from src.main import qb_connector

    if not qb_connector:
        return {"connected": False, "error": "Connector not initialized"}

    return {
        "connected": qb_connector.is_authenticated,
        "realm_id": qb_connector.realm_id,
        "environment": qb_connector.environment,
        "token_expired": qb_connector.is_token_expired,
    }


# ==================== Company Info ====================

@router.get("/company")
async def get_company_info():
    """Get company information."""
    qb = get_qb_connector()
    try:
        data = await qb.get_company_info()
        return data.get("CompanyInfo", {})
    except Exception as e:
        logger.error(f"Failed to get company info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Customers ====================

@router.get("/customers")
async def get_customers():
    """Get all customers."""
    qb = get_qb_connector()
    try:
        customers = await qb.get_customers()
        return {"customers": customers, "count": len(customers)}
    except Exception as e:
        logger.error(f"Failed to get customers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get a specific customer."""
    qb = get_qb_connector()
    try:
        customer = await qb.get_customer(customer_id)
        return customer
    except Exception as e:
        logger.error(f"Failed to get customer {customer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/customers")
async def create_customer(customer_data: dict):
    """Create a new customer."""
    qb = get_qb_connector()
    try:
        customer = await qb.create_customer(customer_data)
        return customer
    except Exception as e:
        logger.error(f"Failed to create customer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Invoices ====================

@router.get("/invoices")
async def get_invoices():
    """Get all invoices."""
    qb = get_qb_connector()
    try:
        invoices = await qb.get_invoices()
        return {"invoices": invoices, "count": len(invoices)}
    except Exception as e:
        logger.error(f"Failed to get invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str):
    """Get a specific invoice."""
    qb = get_qb_connector()
    try:
        invoice = await qb.get_invoice(invoice_id)
        return invoice
    except Exception as e:
        logger.error(f"Failed to get invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices")
async def create_invoice(invoice_data: dict):
    """Create a new invoice."""
    qb = get_qb_connector()
    try:
        invoice = await qb.create_invoice(invoice_data)
        return invoice
    except Exception as e:
        logger.error(f"Failed to create invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Payments ====================

@router.get("/payments")
async def get_payments():
    """Get all payments."""
    qb = get_qb_connector()
    try:
        payments = await qb.get_payments()
        return {"payments": payments, "count": len(payments)}
    except Exception as e:
        logger.error(f"Failed to get payments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments")
async def create_payment(payment_data: dict):
    """Create a new payment."""
    qb = get_qb_connector()
    try:
        payment = await qb.create_payment(payment_data)
        return payment
    except Exception as e:
        logger.error(f"Failed to create payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chart of Accounts ====================

@router.get("/accounts")
async def get_accounts():
    """Get chart of accounts."""
    qb = get_qb_connector()
    try:
        accounts = await qb.get_accounts()
        return {"accounts": accounts, "count": len(accounts)}
    except Exception as e:
        logger.error(f"Failed to get accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Vendors/Contractors ====================

@router.get("/vendors")
async def get_vendors():
    """Get all vendors/contractors."""
    qb = get_qb_connector()
    try:
        vendors = await qb.get_vendors()
        return {"vendors": vendors, "count": len(vendors)}
    except Exception as e:
        logger.error(f"Failed to get vendors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: str):
    """Get a specific vendor/contractor."""
    qb = get_qb_connector()
    try:
        vendor = await qb.get_vendor(vendor_id)
        return vendor
    except Exception as e:
        logger.error(f"Failed to get vendor {vendor_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vendors")
async def create_vendor(vendor_data: dict):
    """Create a new vendor/contractor.

    Example payload:
    {
        "DisplayName": "John Contractor",
        "GivenName": "John",
        "FamilyName": "Contractor",
        "CompanyName": "John's Services",
        "Vendor1099": true,
        "BillRate": 50.00,
        "PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"},
        "PrimaryEmailAddr": {"Address": "john@example.com"},
        "BillAddr": {
            "Line1": "123 Main St",
            "City": "Los Angeles",
            "CountrySubDivisionCode": "CA",
            "PostalCode": "90001"
        }
    }
    """
    qb = get_qb_connector()
    try:
        vendor = await qb.create_vendor(vendor_data)
        return vendor
    except Exception as e:
        logger.error(f"Failed to create vendor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vendors/bulk")
async def bulk_create_vendors(vendors: list):
    """Bulk create vendors/contractors.

    Example payload:
    [
        {"DisplayName": "Contractor 1", "GivenName": "John", "FamilyName": "Doe", "Vendor1099": true, "BillRate": 45.00},
        {"DisplayName": "Contractor 2", "GivenName": "Jane", "FamilyName": "Smith", "Vendor1099": true, "BillRate": 55.00}
    ]
    """
    qb = get_qb_connector()
    results = {"created": [], "errors": []}

    for vendor_data in vendors:
        try:
            vendor = await qb.create_vendor(vendor_data)
            results["created"].append(vendor)
        except Exception as e:
            results["errors"].append({
                "vendor": vendor_data.get("DisplayName", "Unknown"),
                "error": str(e)
            })

    return {
        "total": len(vendors),
        "created_count": len(results["created"]),
        "error_count": len(results["errors"]),
        "created": results["created"],
        "errors": results["errors"]
    }


# ==================== Bills ====================

@router.get("/bills")
async def get_bills():
    """Get all bills."""
    qb = get_qb_connector()
    try:
        bills = await qb.get_bills()
        return {"bills": bills, "count": len(bills)}
    except Exception as e:
        logger.error(f"Failed to get bills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
