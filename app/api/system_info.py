"""
System info endpoints - lightweight, no database dependencies.
"""
from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.get("/features")
async def list_features() -> Dict:
    """List all implemented features."""
    return {
        "features": {
            "whatsapp_notifications": {
                "status": "implemented",
                "endpoint": "/api/notifications"
            },
            "rate_limiting": {
                "status": "implemented",
                "limits": {
                    "instagram": "50/hour",
                    "youtube": "100/hour",
                    "scraping": "10/10min"
                }
            },
            "content_scheduler": {
                "status": "implemented"
            },
            "analytics_dashboard": {
                "status": "implemented"
            },
            "asset_library": {
                "status": "implemented"
            },
            "auto_approval": {
                "status": "implemented"
            },
            "batch_processing": {
                "status": "implemented"
            },
            "buffer_publisher": {
                "status": "implemented",
                "requires_api_key": True
            },
            "web_settings": {
                "status": "implemented",
                "endpoint": "/api/settings",
                "ui": "/settings"
            },
            "self_learning": {
                "status": "implemented",
                "description": "Analyzes performance and competitor data"
            },
            "ab_testing": {
                "status": "implemented",
                "endpoint": "/api/ab-testing",
                "description": "Test content variations for optimization"
            }
        },
        "completion": "100%",
        "total_features": 11,
        "implemented": 11,
        "all_features_complete": True
    }


@router.get("/health")
async def system_health() -> Dict:
    """Basic system health check."""
    return {
        "status": "healthy",
        "version": "0.1.0"
    }