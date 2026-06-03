"""
Settings API endpoints for web-based configuration.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from app.core.settings_service import get_settings_service, get_setting


router = APIRouter()


class SettingUpdate(BaseModel):
    """Model for updating a setting."""
    value: Any
    value_type: Optional[str] = "string"


class SettingResponse(BaseModel):
    """Model for setting response."""
    key: str
    value: Any
    type: str
    category: str
    description: str
    is_sensitive: bool


@router.get("")
async def list_settings(category: Optional[str] = None) -> Dict:
    """
    List all settings, optionally filtered by category.
    
    Categories: notifications, publishing, ai, media, application
    """
    service = get_settings_service()
    settings = await service.get_all(category)
    
    return {"settings": settings}


@router.get("/categories")
async def list_categories() -> Dict:
    """List all setting categories."""
    service = get_settings_service()
    all_settings = await service.get_all()
    
    categories = set()
    for key, data in all_settings.items():
        categories.add(data["category"])
    
    return {
        "categories": sorted(list(categories)),
        "count": len(categories)
    }


@router.get("/{key}")
async def get_setting_value(key: str) -> Dict:
    """Get a specific setting value."""
    service = get_settings_service()
    all_settings = await service.get_all()
    
    if key not in all_settings:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    
    return {"setting": {"key": key, **all_settings[key]}}


@router.put("/{key}")
async def update_setting(key: str, update: SettingUpdate) -> Dict:
    """Update a setting value."""
    service = get_settings_service()
    all_settings = await service.get_all()
    
    if key not in all_settings:
        # Create new setting
        await service.set(key, update.value, update.value_type)
        return {"success": True, "message": f"Setting '{key}' created"}
    
    await service.set(key, update.value, update.value_type)
    return {"success": True, "message": f"Setting '{key}' updated"}


@router.delete("/{key}")
async def delete_setting(key: str) -> Dict:
    """Delete a setting."""
    service = get_settings_service()
    all_settings = await service.get_all()
    
    if key not in all_settings:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    
    await service.delete(key)
    return {"success": True, "message": f"Setting '{key}' deleted"}


@router.get("/category/{category}")
async def get_category_settings(category: str) -> Dict:
    """Get all settings for a specific category."""
    service = get_settings_service()
    settings = await service.get_category(category)
    
    return {"category": category, "settings": settings}


# Convenience endpoints for common settings
@router.get("/whatsapp/status")
async def whatsapp_status() -> Dict:
    """Get WhatsApp configuration status."""
    enabled = await get_setting("whatsapp_enabled", False)
    phone = await get_setting("whatsapp_phone_number", "")
    
    return {
        "enabled": enabled,
        "phone_configured": bool(phone),
        "phone": phone[:3] + "***" + phone[-3:] if phone and len(phone) > 6 else ""
    }


@router.get("/publishing/status")
async def publishing_status() -> Dict:
    """Get publishing configuration status."""
    buffer_key = await get_setting("buffer_api_key", "")
    meta_token = await get_setting("meta_access_token", "")
    youtube_key = await get_setting("youtube_api_key", "")
    
    return {
        "buffer_configured": bool(buffer_key),
        "meta_configured": bool(meta_token),
        "youtube_configured": bool(youtube_key),
        "platforms_available": [
            p for p, configured in [
                ("buffer", bool(buffer_key)),
                ("meta", bool(meta_token)),
                ("youtube", bool(youtube_key))
            ] if configured
        ]
    }