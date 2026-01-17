"""
Patagon Accounting - QuickBooks Integration

FastAPI application for QuickBooks Online accounting integration.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Patagon Accounting",
    description="QuickBooks Online Integration for Patagon Consulting",
    version="1.0.0",
)


@app.get("/")
async def home():
    """Home page."""
    return {"message": "Patagon Accounting API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy", "service": "patagon-accounting"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
