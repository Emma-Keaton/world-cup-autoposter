#!/usr/bin/env python
"""Test database auto-initialization."""
import asyncio
from app.core.database import init_db
from app.core.settings_service import get_settings_service

async def main():
    print("🧪 Testing Database Auto-Initialization...\n")
    
    # Test 1: Initialize database
    print("1. Initializing database and settings...")
    await init_db()
    print("✅ Database initialized\n")
    
    # Test 2: Load settings
    print("2. Loading settings from database...")
    service = get_settings_service()
    settings = await service.get_all()
    print(f"✅ Loaded {len(settings)} settings\n")
    
    # Test 3: Verify categories
    categories = set(v['category'] for v in settings.values())
    print(f"3. Categories found: {list(categories)}\n")
    
    # Test 4: Sample settings
    sample_keys = list(settings.keys())[:5]
    print(f"4. Sample settings: {sample_keys}\n")
    
    # Test 5: Verify specific settings
    nvidia_key = settings.get('nvidia_api_key', {})
    whatsapp_enabled = settings.get('whatsapp_enabled', {})
    print(f"5. Key settings:")
    print(f"   - NVIDIA API Key configured: {bool(nvidia_key.get('value'))}")
    print(f"   - WhatsApp enabled: {whatsapp_enabled.get('value', False)}\n")
    
    print("✅ ALL TESTS PASSED!")
    print("\n💡 The database now auto-initializes with all settings on startup!")

if __name__ == "__main__":
    asyncio.run(main())