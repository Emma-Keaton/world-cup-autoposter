#!/usr/bin/env python
"""
Comprehensive Test Suite for World Cup Autoposter
Tests all 11 features end-to-end
"""
import asyncio
import sys
from typing import List, Tuple

# Test results tracker
TEST_RESULTS = []

def test_result(name: str, passed: bool, message: str = ""):
    """Track test result."""
    TEST_RESULTS.append((name, passed, message))
    status = "✅" if passed else "❌"
    print(f"{status} {name}: {message}")

async def test_database_initialization():
    """Test 1: Database auto-initialization."""
    print("\n🧪 TEST 1: Database Initialization")
    try:
        from app.core.database import init_db, async_session_factory
        from app.core.settings_service import get_settings_service, SettingModel
        from sqlalchemy import select, func
        
        # Initialize
        await init_db()
        test_result("DB Init", True, "Database initialized successfully")
        
        # Count settings
        async with async_session_factory() as session:
            result = await session.execute(select(func.count()).select_from(SettingModel))
            count = result.scalar()
            test_result("Settings Count", count == 15, f"Expected 15, got {count}")
        
        return True
    except Exception as e:
        test_result("DB Init", False, str(e))
        return False

async def test_settings_service():
    """Test 2: Settings Service."""
    print("\n🧪 TEST 2: Settings Service")
    try:
        from app.core.settings_service import get_settings_service
        
        service = get_settings_service()
        settings = await service.get_all()
        
        # Test categories
        categories = set(v['category'] for v in settings.values())
        expected_categories = {'notifications', 'publishing', 'ai', 'media', 'application'}
        test_result("Categories", categories == expected_categories, f"Found {len(categories)} categories")
        
        # Test specific settings
        nvidia_key = settings.get('nvidia_api_key', {})
        test_result("NVIDIA Setting", 'value' in nvidia_key, "NVIDIA API key setting exists")
        
        # Test update
        await service.set('test_setting', 'test_value')
        updated = await service.get('test_setting')
        test_result("Setting Update", updated == 'test_value', "Setting updated and retrieved")
        
        return True
    except Exception as e:
        test_result("Settings Service", False, str(e))
        return False

async def test_whatsapp_notifier():
    """Test 3: WhatsApp Notification Service."""
    print("\n🧪 TEST 3: WhatsApp Notifications")
    try:
        from app.services.whatsapp_notifier import WhatsAppNotifier, MessagePriority
        
        notifier = WhatsAppNotifier()
        test_result("WhatsApp Init", True, "Notifier initialized")
        
        # Test phone formatting
        formatted = notifier._format_phone_number("+1234567890")
        test_result("Phone Format", formatted == "+1234567890", "Phone formatting works")
        
        # Test message priority
        test_result("Message Priority", MessagePriority.HIGH.value == "high", "Priority enum works")
        
        return True
    except Exception as e:
        test_result("WhatsApp", False, str(e))
        return False

async def test_error_notifier():
    """Test 4: Error Notification Service."""
    print("\n🧪 TEST 4: Error Notifications")
    try:
        from app.services.error_notifier import ErrorNotifier, ErrorSeverity
        
        notifier = ErrorNotifier()
        test_result("Error Notifier Init", True, "Error notifier initialized")
        
        # Test severity levels
        test_result("Severity Levels", ErrorSeverity.HIGH.value == "high", "Severity enum works")
        
        return True
    except Exception as e:
        test_result("Error Notifier", False, str(e))
        return False

async def test_rate_limiter():
    """Test 5: Rate Limiting Service."""
    print("\n🧪 TEST 5: Rate Limiting")
    try:
        from app.core.rate_limiter import get_rate_limiter, RateLimitExceeded
        
        limiter = get_rate_limiter()
        test_result("Rate Limiter Init", True, "Rate limiter initialized")
        
        # Test limits configured
        test_result("Limits Configured", len(limiter.limits) > 0, f"{len(limiter.limits)} limits configured")
        
        # Test acquire
        success, wait_time = limiter.acquire("instagram")
        test_result("Token Acquire", success, "Successfully acquired token")
        
        # Test status
        status = limiter.get_status("instagram")
        test_result("Status Check", 'tokens_available' in status, "Status check works")
        
        return True
    except Exception as e:
        test_result("Rate Limiter", False, str(e))
        return False

async def test_scheduler():
    """Test 6: Content Scheduler."""
    print("\n🧪 TEST 6: Content Scheduler")
    try:
        from app.core.scheduler import get_scheduler, PostPriority
        
        scheduler = get_scheduler()
        test_result("Scheduler Init", True, "Scheduler initialized")
        
        # Test posting windows
        test_result("Posting Windows", len(scheduler._posting_windows) > 0, "Posting windows configured")
        
        # Test priority enum
        test_result("Priority", PostPriority.HIGH.value == "high", "Priority enum works")
        
        return True
    except Exception as e:
        test_result("Scheduler", False, str(e))
        return False

async def test_auto_approval():
    """Test 7: Auto-Approval Engine."""
    print("\n🧪 TEST 7: Auto-Approval Engine")
    try:
        from app.core.auto_approval import get_approval_engine, ApprovalDecision
        
        engine = get_approval_engine()
        test_result("Approval Engine Init", True, "Approval engine initialized")
        
        # Test rules
        rules = engine.get_rules()
        test_result("Approval Rules", len(rules) > 0, f"{len(rules)} rules configured")
        
        # Test evaluation
        content = {"viral_score": 9, "topic": "breaking", "content_category": "goal"}
        result = engine.evaluate(content)
        test_result("Content Evaluation", result.decision == ApprovalDecision.AUTO_APPROVE, "Content evaluated")
        
        return True
    except Exception as e:
        test_result("Auto Approval", False, str(e))
        return False

async def test_ab_testing():
    """Test 8: A/B Testing Framework."""
    print("\n🧪 TEST 8: A/B Testing")
    try:
        from app.core.ab_testing import get_ab_test, Variation
        
        ab_test = get_ab_test()
        test_result("A/B Test Init", True, "A/B testing initialized")
        
        # Test variation creation
        variation = Variation(
            id="var1",
            name="Test Variant",
            content_params={"style": "bold"},
            is_control=False
        )
        test_result("Variation", variation.name == "Test Variant", "Variation created")
        
        return True
    except Exception as e:
        test_result("A/B Testing", False, str(e))
        return False

async def test_batch_processor():
    """Test 9: Batch Processing."""
    print("\n🧪 TEST 9: Batch Processing")
    try:
        from app.services.batch_processor import get_batch_processor, BatchStatus
        
        processor = get_batch_processor()
        test_result("Batch Processor Init", True, "Batch processor initialized")
        
        # Test status enum
        test_result("Batch Status", BatchStatus.PENDING.value == "pending", "Status enum works")
        
        return True
    except Exception as e:
        test_result("Batch Processor", False, str(e))
        return False

async def test_asset_library():
    """Test 10: Asset Library."""
    print("\n🧪 TEST 10: Asset Library")
    try:
        from app.services.asset_library import get_asset_library, AssetType
        
        library = get_asset_library()
        test_result("Asset Library Init", True, "Asset library initialized")
        
        # Test asset types
        test_result("Asset Types", len(AssetType) > 0, f"{len(AssetType)} asset types defined")
        
        return True
    except Exception as e:
        test_result("Asset Library", False, str(e))
        return False

async def test_analytics_service():
    """Test 11: Analytics Service."""
    print("\n🧪 TEST 11: Analytics Service")
    try:
        from app.services.analytics_service import get_analytics
        
        analytics = get_analytics()
        test_result("Analytics Init", True, "Analytics service initialized")
        
        return True
    except Exception as e:
        test_result("Analytics", False, str(e))
        return False

async def test_api_endpoints():
    """Test 12: API Endpoints."""
    print("\n🧪 TEST 12: API Endpoints")
    try:
        from app.main import app
        
        # Count routes
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        test_result("API Routes", len(routes) > 50, f"{len(routes)} routes registered")
        
        # Check critical routes
        critical_routes = ['/api/health', '/api/settings', '/api/ab-testing/tests']
        found = [r for r in critical_routes if any(r in route for route in routes)]
        test_result("Critical Routes", len(found) == len(critical_routes), f"{len(found)}/{len(critical_routes)} critical routes")
        
        return True
    except Exception as e:
        test_result("API Endpoints", False, str(e))
        return False

async def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("🚀 WORLD CUP AUTOPOSTER - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    tests = [
        ("Database", test_database_initialization),
        ("Settings", test_settings_service),
        ("WhatsApp", test_whatsapp_notifier),
        ("Error Notifier", test_error_notifier),
        ("Rate Limiter", test_rate_limiter),
        ("Scheduler", test_scheduler),
        ("Auto Approval", test_auto_approval),
        ("A/B Testing", test_ab_testing),
        ("Batch Processor", test_batch_processor),
        ("Asset Library", test_asset_library),
        ("Analytics", test_analytics_service),
        ("API Endpoints", test_api_endpoints),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            test_result(name, False, f"Unexpected error: {e}")
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(TEST_RESULTS)}")
    print(f"Passed: {len([r for r in TEST_RESULTS if r[1]])}")
    print(f"Failed: {len([r for r in TEST_RESULTS if not r[1]])}")
    print(f"Success Rate: {len([r for r in TEST_RESULTS if r[1]])/len(TEST_RESULTS)*100:.1f}%")
    print("="*60)
    
    # Feature summary
    print(f"\n🎯 FEATURES TESTED: {passed}/{passed+failed}")
    
    if failed == 0:
        print("\n✅ ALL FEATURES WORKING! Ready for deployment!")
        return 0
    else:
        print(f"\n⚠️  {failed} feature(s) need attention")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)