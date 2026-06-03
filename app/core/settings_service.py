"""
Application Settings management.
Stores API keys and configuration in database for web-based management.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, DateTime, Integer, JSON

from app.core.database import Base, async_session_factory
from app.core.config import settings as env_settings


class SettingModel(Base):
    """Database model for application settings."""
    
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    value_type: Mapped[str] = mapped_column(String(20), default="string")  # string, bool, int, json
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)  # Hide in UI
    category: Mapped[str] = mapped_column(String(50), default="general")
    description: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default='now()', onupdate='now')


class SettingsService:
    """
    Service for managing application settings via database.
    
    Falls back to .env for values not in database.
    """
    
    # Default settings schema
    DEFAULT_SETTINGS = {
        # WhatsApp
        "whatsapp_enabled": {"default": False, "type": "bool", "category": "notifications", "description": "Enable WhatsApp error notifications"},
        "whatsapp_phone_number": {"default": "", "type": "string", "category": "notifications", "description": "Phone number to receive WhatsApp alerts"},
        "whatsapp_session_file": {"default": "whatsapp_session.json", "type": "string", "category": "notifications", "description": "WhatsApp session file path"},
        
        # Buffer API
        "buffer_api_key": {"default": "", "type": "string", "category": "publishing", "description": "Buffer API key for social media posting", "is_sensitive": True},
        
        # NVIDIA API
        "nvidia_api_key": {"default": "", "type": "string", "category": "ai", "description": "NVIDIA NIM API key", "is_sensitive": True},
        "nvidia_api_base_url": {"default": "https://integrate.api.nvidia.com/v1", "type": "string", "category": "ai", "description": "NVIDIA API base URL"},
        
        # Social Media APIs
        "meta_access_token": {"default": "", "type": "string", "category": "publishing", "description": "Meta/Facebook access token", "is_sensitive": True},
        "instagram_business_account_id": {"default": "", "type": "string", "category": "publishing", "description": "Instagram Business Account ID"},
        "youtube_api_key": {"default": "", "type": "string", "category": "publishing", "description": "YouTube Data API key", "is_sensitive": True},
        "youtube_channel_id": {"default": "", "type": "string", "category": "publishing", "description": "YouTube Channel ID"},
        
        # Stock Media
        "pexels_api_key": {"default": "", "type": "string", "category": "media", "description": "Pexels API key", "is_sensitive": True},
        "pixabay_api_key": {"default": "", "type": "string", "category": "media", "description": "Pixabay API key", "is_sensitive": True},
        
        # App Settings
        "app_env": {"default": "development", "type": "string", "category": "application", "description": "Application environment"},
        "debug_mode": {"default": True, "type": "bool", "category": "application", "description": "Enable debug mode"},
        "log_level": {"default": "INFO", "type": "string", "category": "application", "description": "Logging level"},
    }
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._initialized = False
        logger.info("SettingsService initialized")
    
    async def initialize(self) -> None:
        """Initialize settings from database and create defaults."""
        if self._initialized:
            return
        
        async with async_session_factory() as session:
            # Create default settings that don't exist
            for key, config in self.DEFAULT_SETTINGS.items():
                result = await session.execute(
                    select(SettingModel).where(SettingModel.key == key)
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    await session.execute(
                        insert(SettingModel).values(
                            key=key,
                            value=str(config["default"]),
                            value_type=config["type"],
                            category=config["category"],
                            description=config["description"],
                            is_sensitive=config.get("is_sensitive", False)
                        )
                    )
            
            await session.commit()
        
        self._initialized = True
        logger.info("SettingsService initialized with defaults")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(SettingModel).where(SettingModel.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                value = self._convert_value(setting.value, setting.value_type)
                self._cache[key] = value
                return value
        
        # Fallback to .env
        env_value = getattr(env_settings, key.upper(), None)
        if env_value is not None:
            return env_value
        
        # Return default
        if key in self.DEFAULT_SETTINGS:
            return self._convert_value(str(self.DEFAULT_SETTINGS[key]["default"]), self.DEFAULT_SETTINGS[key]["type"])
        
        return default
    
    async def set(self, key: str, value: Any, value_type: str = "string") -> bool:
        """Set a setting value."""
        str_value = str(value) if value_type != "json" else str(value)
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(SettingModel).where(SettingModel.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                await session.execute(
                    update(SettingModel)
                    .where(SettingModel.key == key)
                    .values(value=str_value, value_type=value_type)
                )
            else:
                await session.execute(
                    insert(SettingModel).values(
                        key=key,
                        value=str_value,
                        value_type=value_type,
                        category="custom"
                    )
                )
            
            await session.commit()
        
        # Update cache
        self._cache[key] = self._convert_value(str_value, value_type)
        return True
    
    async def get_all(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get all settings, optionally filtered by category."""
        async with async_session_factory() as session:
            query = select(SettingModel).order_by(SettingModel.category, SettingModel.key)
            
            if category:
                query = query.where(SettingModel.category == category)
            
            result = await session.execute(query)
            settings = result.scalars().all()
            
            return {
                s.key: {
                    "value": self._convert_value(s.value, s.value_type),
                    "type": s.value_type,
                    "category": s.category,
                    "description": s.description,
                    "is_sensitive": s.is_sensitive
                }
                for s in settings
            }
    
    async def get_category(self, category: str) -> Dict[str, Any]:
        """Get all settings for a specific category."""
        return await self.get_all(category)
    
    def _convert_value(self, value: str, value_type: str) -> Any:
        """Convert string value to appropriate type."""
        if value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "int":
            return int(value) if value.isdigit() else 0
        elif value_type == "json":
            import json
            try:
                return json.loads(value)
            except:
                return {}
        else:
            return value
    
    async def delete(self, key: str) -> bool:
        """Delete a setting."""
        from sqlalchemy import delete
        
        async with async_session_factory() as session:
            await session.execute(
                delete(SettingModel).where(SettingModel.key == key)
            )
            await session.commit()
        
        # Clear cache
        self._cache.pop(key, None)
        return True


# Global instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get the global settings service instance."""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service


async def get_setting(key: str, default: Any = None) -> Any:
    """Convenience function to get a setting."""
    service = get_settings_service()
    return await service.get(key, default)


async def set_setting(key: str, value: Any, value_type: str = "string") -> bool:
    """Convenience function to set a setting."""
    service = get_settings_service()
    return await service.set(key, value, value_type)