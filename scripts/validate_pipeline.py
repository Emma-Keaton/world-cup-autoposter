"""
Validation script for the enhanced pipeline modules.
Tests that all new modules can be imported and initialized.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all new modules can be imported."""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)
    
    tests = []
    
    # Test 1: Enhanced Video Renderer
    try:
        from app.renderer.video_renderer_enhanced import EnhancedVideoRenderer, SOCIAL_MEDIA_PRESETS
        print("✅ video_renderer_enhanced: OK")
        print(f"   - Presets available: {list(SOCIAL_MEDIA_PRESETS.keys())}")
        tests.append(("video_renderer_enhanced", True, None))
    except Exception as e:
        print(f"❌ video_renderer_enhanced: FAILED - {e}")
        tests.append(("video_renderer_enhanced", False, str(e)))
    
    # Test 2: Clip Sequence Planner
    try:
        from app.renderer.clip_sequence_planner import ClipSequencePlanner, SequencePlan, SmartClipAssembler, VisualType, NarrativeRole
        print("✅ clip_sequence_planner: OK")
        print(f"   - Visual types: {[v.value for v in VisualType]}")
        print(f"   - Narrative roles: {[n.value for n in NarrativeRole]}")
        tests.append(("clip_sequence_planner", True, None))
    except Exception as e:
        print(f"❌ clip_sequence_planner: FAILED - {e}")
        tests.append(("clip_sequence_planner", False, str(e)))
    
    # Test 3: Advanced Clip Editor
    try:
        from app.renderer.advanced_clip_editor import AdvancedClipEditor, EditSettings
        print("✅ advanced_clip_editor: OK")
        tests.append(("advanced_clip_editor", True, None))
    except Exception as e:
        print(f"❌ advanced_clip_editor: FAILED - {e}")
        tests.append(("advanced_clip_editor", False, str(e)))
    
    # Test 4: Copyright Safety Checker
    try:
        from app.core.copyright_checker import CopyrightSafetyChecker, RiskLevel, FairUseFactor, ContentIDAvoidance
        print("✅ copyright_checker: OK")
        print(f"   - Risk levels: {[r.value for r in RiskLevel]}")
        print(f"   - Fair use factors: {[f.value for f in FairUseFactor]}")
        tests.append(("copyright_checker", True, None))
    except Exception as e:
        print(f"❌ copyright_checker: FAILED - {e}")
        tests.append(("copyright_checker", False, str(e)))
    
    # Test 5: Competitor Monitor
    try:
        from app.core.competitor_monitor import CompetitorMonitor, ContentSuggestionEngine, INSPIRATION_CHANNELS
        print("✅ competitor_monitor: OK")
        print(f"   - Monitored channels: {len(INSPIRATION_CHANNELS)}")
        for ch in INSPIRATION_CHANNELS[:3]:
            print(f"      - {ch.name} ({ch.content_type}, risk: {ch.copyright_risk})")
        tests.append(("competitor_monitor", True, None))
    except Exception as e:
        print(f"❌ competitor_monitor: FAILED - {e}")
        tests.append(("competitor_monitor", False, str(e)))
    
    # Test 6: Pipeline Orchestrator
    try:
        from app.renderer.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig, PipelineResult
        print("✅ pipeline_orchestrator: OK")
        tests.append(("pipeline_orchestrator", True, None))
    except Exception as e:
        print(f"❌ pipeline_orchestrator: FAILED - {e}")
        tests.append(("pipeline_orchestrator", False, str(e)))
    
    # Test 7: Pipeline API Router
    try:
        from app.api.pipeline import router as pipeline_router
        print("✅ pipeline API router: OK")
        tests.append(("pipeline_api", True, None))
    except Exception as e:
        print(f"❌ pipeline API router: FAILED - {e}")
        tests.append(("pipeline_api", False, str(e)))
    
    # Test 8: External Dependencies
    print("\n" + "-" * 60)
    print("TESTING EXTERNAL DEPENDENCIES")
    print("-" * 60)
    
    try:
        import feedparser
        print(f"✅ feedparser: v{feedparser.__version__}")
        tests.append(("feedparser", True, None))
    except Exception as e:
        print(f"❌ feedparser: FAILED - {e}")
        tests.append(("feedparser", False, str(e)))
    
    try:
        import imagehash
        print(f"✅ imagehash: OK")
        tests.append(("imagehash", True, None))
    except Exception as e:
        print(f"❌ imagehash: FAILED - {e}")
        tests.append(("imagehash", False, str(e)))
    
    try:
        import librosa
        print(f"✅ librosa: v{librosa.__version__}")
        tests.append(("librosa", True, None))
    except Exception as e:
        print(f"❌ librosa: FAILED - {e}")
        tests.append(("librosa", False, str(e)))
    
    try:
        import faster_whisper
        print(f"✅ faster-whisper: OK")
        tests.append(("faster_whisper", True, None))
    except Exception as e:
        print(f"❌ faster-whisper: FAILED - {e}")
        tests.append(("faster_whisper", False, str(e)))
    
    try:
        import edge_tts
        print(f"✅ edge-tts: OK")
        tests.append(("edge_tts", True, None))
    except Exception as e:
        print(f"❌ edge-tts: FAILED - {e}")
        tests.append(("edge_tts", False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, p, _ in tests if p)
    failed = sum(1 for _, p, _ in tests if not p)
    
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for name, passed, error in tests:
            if not passed:
                print(f"  - {name}: {error}")
    
    return failed == 0


async def test_basic_functionality():
    """Test basic functionality of key components."""
    print("\n" + "=" * 60)
    print("FUNCTIONALITY TESTS")
    print("=" * 60)
    
    tests_passed = True
    
    # Test 1: Create pipeline config
    try:
        from app.renderer.pipeline_orchestrator import PipelineConfig
        config = PipelineConfig(
            platform="youtube_shorts",
            edit_style="heavy_editing",
        )
        print(f"✅ PipelineConfig created: platform={config.platform}, style={config.edit_style}")
    except Exception as e:
        print(f"❌ PipelineConfig failed: {e}")
        tests_passed = False
    
    # Test 2: Create clip sequence planner
    try:
        from app.renderer.clip_sequence_planner import ClipSequencePlanner
        planner = ClipSequencePlanner(max_clip_duration=5.0)
        print(f"✅ ClipSequencePlanner created: max_clip={planner.max_clip_duration}s")
    except Exception as e:
        print(f"❌ ClipSequencePlanner failed: {e}")
        tests_passed = False
    
    # Test 3: Initialize copyright checker
    try:
        from app.core.copyright_checker import CopyrightSafetyChecker
        checker = CopyrightSafetyChecker()
        print(f"✅ CopyrightSafetyChecker initialized")
    except Exception as e:
        print(f"❌ CopyrightSafetyChecker failed: {e}")
        tests_passed = False
    
    # Test 4: Initialize competitor monitor
    try:
        from app.core.competitor_monitor import CompetitorMonitor
        monitor = CompetitorMonitor()
        stats = monitor.get_channel_stats()
        print(f"✅ CompetitorMonitor initialized: {stats['total_channels']} channels")
    except Exception as e:
        print(f"❌ CompetitorMonitor failed: {e}")
        tests_passed = False
    
    # Test 5: Create enhanced renderer
    try:
        from app.renderer.video_renderer_enhanced import EnhancedVideoRenderer
        renderer = EnhancedVideoRenderer()
        print(f"✅ EnhancedVideoRenderer initialized")
    except Exception as e:
        print(f"❌ EnhancedVideoRenderer failed: {e}")
        tests_passed = False
    
    # Test 6: Create advanced editor
    try:
        from app.renderer.advanced_clip_editor import AdvancedClipEditor
        editor = AdvancedClipEditor()
        print(f"✅ AdvancedClipEditor initialized")
    except Exception as e:
        print(f"❌ AdvancedClipEditor failed: {e}")
        tests_passed = False
    
    return tests_passed


async def main():
    """Run all validation tests."""
    print("\n" + "🚀 WORLD CUP AUTOPOSTER - PIPELINE VALIDATION")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test functionality
    functionality_ok = await test_basic_functionality()
    
    # Final result
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if imports_ok and functionality_ok:
        print("✅ ALL TESTS PASSED - Pipeline ready for use!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)