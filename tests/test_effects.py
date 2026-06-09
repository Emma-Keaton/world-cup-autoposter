"""Tests for the video effects engine."""

import pytest
import math
from unittest.mock import MagicMock, patch

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType
from app.effects.easing import (
    power2_out, expo_out, back_out, elastic_out, bounce_out,
    spring_ease, critical_damping_ratio, SPRING_DEFAULT, SPRING_GENTLE,
    ffmpeg_sine_expr, ffmpeg_spring_zoom_expr, ffmpeg_shake_expr,
    interpolate_keyframes,
)
from app.effects.particles import (
    Particle, emit_confetti, emit_explosion, emit_fountain,
    step_particles, color_gradient_fire, color_gradient_confetti,
)
from app.effects.audio_analyzer import smooth_envelope
from app.effects.emotion_visuals import infer_emotion, EMOTION_EFFECT_MAP


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_ctx():
    """Basic effect context for testing."""
    return EffectContext(
        clip_path="/tmp/test.mp4",
        duration=5.0,
        fps=30,
        width=1080,
        height=1920,
        intensity=0.5,
        narrative_role="climax",
        visual_type="action",
        effect_tags=["dramatic_pause", "slow_motion"],
    )


@pytest.fixture
def low_intensity_ctx():
    return EffectContext(
        clip_path="/tmp/test.mp4",
        duration=5.0,
        intensity=0.2,
        narrative_role="hook",
        visual_type="action",
        effect_tags=["zoom_in", "fast_pace"],
    )


# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------

class TestEasingFunctions:
    def test_power2_out_starts_at_0(self):
        assert power2_out(0) == 0

    def test_power2_out_ends_at_1(self):
        assert abs(power2_out(1) - 1) < 0.001

    def test_expo_out_bounds(self):
        assert expo_out(0) == 0
        assert expo_out(1) == 1

    def test_back_out_overshoots(self):
        """back.out should exceed 1.0 briefly (overshoot)."""
        values = [back_out(t / 100) for t in range(101)]
        assert max(values) > 1.0

    def test_elastic_out_oscillates(self):
        values = [elastic_out(t / 100) for t in range(101)]
        # Should exceed 1.0 at some point
        assert max(values) > 1.0

    def test_bounce_out_ends_at_1(self):
        assert abs(bounce_out(1) - 1) < 0.01

    def test_spring_ease_reaches_1(self):
        result = spring_ease(2.0, **SPRING_DEFAULT)
        assert abs(result - 1.0) < 0.01

    def test_spring_ease_gentle(self):
        result = spring_ease(3.0, **SPRING_GENTLE)
        assert abs(result - 1.0) < 0.01

    def test_critical_damping_underdamped(self):
        zeta = critical_damping_ratio(tension=170, friction=20)
        assert zeta < 1.0  # Under-damped

    def test_critical_damping_overdamped(self):
        zeta = critical_damping_ratio(tension=170, friction=60)
        assert zeta > 1.0  # Over-damped

    def test_interpolate_keyframes_length(self):
        result = interpolate_keyframes(0, 100, 10, power2_out)
        assert len(result) == 10

    def test_interpolate_keyframes_range(self):
        result = interpolate_keyframes(0, 1, 20, power2_out)
        assert result[0] == pytest.approx(0, abs=0.01)
        assert result[-1] == pytest.approx(1, abs=0.01)


# ---------------------------------------------------------------------------
# FFmpeg expression generators
# ---------------------------------------------------------------------------

class TestFFmpegExpressions:
    def test_sine_expr_format(self):
        expr = ffmpeg_sine_expr("t", 10, 0.8, 0, 0)
        assert "sin" in expr
        assert "10" in expr

    def test_spring_zoom_expr_contains_if(self):
        expr = ffmpeg_spring_zoom_expr(1.0, 1.3, 1.15, 6, 20)
        assert "if" in expr
        assert "exp" in expr

    def test_shake_expr_format(self):
        expr = ffmpeg_shake_expr("x", 8, 15, 3, 0, 15)
        assert "sin" in expr
        assert "exp" in expr


# ---------------------------------------------------------------------------
# Base effect classes
# ---------------------------------------------------------------------------

class TestBaseEffect:
    def test_matches_returns_true_for_matching_tag(self):
        class TestEffect(BaseEffect):
            name = "test"
            handled_tags = ["dramatic_pause"]

        effect = TestEffect()
        assert effect.matches(["dramatic_pause", "slow_motion"]) is True

    def test_matches_returns_false_for_no_overlap(self):
        class TestEffect(BaseEffect):
            name = "test"
            handled_tags = ["zoom_in"]

        effect = TestEffect()
        assert effect.matches(["slow_motion"]) is False

    def test_scale_multiplies_by_intensity(self):
        assert BaseEffect.scale(10, 0.5) == 5.0
        assert BaseEffect.scale(10, 1.0) == 10.0
        assert BaseEffect.scale(10, 0.0) == 0.0


class TestEffectContext:
    def test_default_values(self, sample_ctx):
        assert sample_ctx.fps == 30
        assert sample_ctx.width == 1080
        assert sample_ctx.height == 1920
        assert sample_ctx.audio_path is None


class TestEffectResult:
    def test_empty_result(self):
        result = EffectResult()
        assert result.filters == []
        assert result.overlay_frames_dir is None

    def test_result_with_filters(self):
        result = EffectResult(filters=["eq=saturation=1.2", "vignette"])
        assert len(result.filters) == 2


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------

class TestParticleSystem:
    def test_emit_confetti_count(self):
        particles = emit_confetti(540, 600, count=50)
        assert len(particles) == 50

    def test_emit_explosion_count(self):
        particles = emit_explosion(540, 600, count=30)
        assert len(particles) == 30

    def test_emit_fountain_count(self):
        particles = emit_fountain(540, 600, count=20)
        assert len(particles) == 20

    def test_particle_lifecycle(self):
        particles = emit_confetti(540, 600, count=10, max_life=0.5)
        assert all(p.alive for p in particles)
        # Step through entire lifetime
        for _ in range(20):
            particles = step_particles(particles, dt=1/30)
        assert len(particles) == 0  # All dead

    def test_particle_life_ratio(self):
        p = Particle(life=0.5, max_life=1.0)
        assert abs(p.life_ratio - 0.5) < 0.01

    def test_color_gradient_fire_fresh(self):
        r, g, b = color_gradient_fire(1.0)
        assert r == 255  # Fresh particle is bright

    def test_color_gradient_fire_dead(self):
        r, g, b = color_gradient_fire(0.0)
        assert r == 0

    def test_color_gradient_confetti_returns_rgb(self):
        r, g, b = color_gradient_confetti(1.0, base_hue=0)
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


# ---------------------------------------------------------------------------
# Audio analysis
# ---------------------------------------------------------------------------

class TestAudioAnalyzer:
    def test_smooth_envelope(self):
        values = [0, 1, 0, 1, 0]
        smoothed = smooth_envelope(values, smoothing=0.5)
        assert len(smoothed) == 5
        # Smoothed values should be less extreme than originals
        assert max(smoothed) < max(values)

    def test_smooth_envelope_no_smoothing(self):
        values = [0.1, 0.5, 0.9]
        smoothed = smooth_envelope(values, smoothing=0.0)
        assert smoothed == values


# ---------------------------------------------------------------------------
# Emotion inference
# ---------------------------------------------------------------------------

class TestEmotionInference:
    def test_climax_is_shock(self, sample_ctx):
        sample_ctx.narrative_role = "climax"
        sample_ctx.visual_type = "reaction"  # reaction maps to shock
        assert infer_emotion(sample_ctx) == "shock"

    def test_build_is_tension(self, sample_ctx):
        sample_ctx.narrative_role = "build"
        sample_ctx.visual_type = "closeup"  # closeup maps to tension
        assert infer_emotion(sample_ctx) == "tension"

    def test_hook_is_energy(self, sample_ctx):
        sample_ctx.narrative_role = "hook"
        sample_ctx.visual_type = "action"  # action maps to energy
        assert infer_emotion(sample_ctx) == "energy"

    def test_payoff_is_joy(self, sample_ctx):
        sample_ctx.narrative_role = "payoff"
        sample_ctx.visual_type = "wide"  # wide has no visual mapping, falls to role
        assert infer_emotion(sample_ctx) == "joy"

    def test_explicit_emotion_overrides(self, sample_ctx):
        sample_ctx.extra_data = {"emotion": "anger"}
        assert infer_emotion(sample_ctx) == "anger"

    def test_emotion_effect_map_has_all_emotions(self):
        for emotion in ["tension", "anger", "joy", "heartbreak", "shock", "energy"]:
            assert emotion in EMOTION_EFFECT_MAP


# ---------------------------------------------------------------------------
# Skill 1: Shot Visuals
# ---------------------------------------------------------------------------

class TestShotVisuals:
    def test_impact_zoom_builds_filter(self, sample_ctx):
        from app.effects.shot_visuals import ImpactZoomEffect
        effect = ImpactZoomEffect()
        result = effect.build(sample_ctx)
        assert len(result.filters) > 0
        assert "zoompan" in result.filters[0]

    def test_impact_zoom_matches_zoom_in(self):
        from app.effects.shot_visuals import ImpactZoomEffect
        effect = ImpactZoomEffect()
        assert effect.matches(["zoom_in"]) is True
        assert effect.matches(["slow_motion"]) is False

    def test_screen_shake_builds_filter(self, sample_ctx):
        from app.effects.shot_visuals import ScreenShakeEffect
        effect = ScreenShakeEffect()
        result = effect.build(sample_ctx)
        assert len(result.filters) > 0

    def test_speed_ramp_builds_filter(self, sample_ctx):
        from app.effects.shot_visuals import SpeedRampEffect
        effect = SpeedRampEffect()
        result = effect.build(sample_ctx)
        assert any("setpts" in f for f in result.filters)

    def test_strobe_flash_builds_filter(self, sample_ctx):
        from app.effects.shot_visuals import StrobeFlashEffect
        effect = StrobeFlashEffect()
        result = effect.build(sample_ctx)
        assert any("eq=brightness" in f for f in result.filters)

    def test_chromatic_aberration_builds_filter(self, sample_ctx):
        from app.effects.shot_visuals import ChromaticAberrationEffect
        effect = ChromaticAberrationEffect()
        result = effect.build(sample_ctx)
        assert any("geq" in f for f in result.filters)


# ---------------------------------------------------------------------------
# Skill 2: Motion Visuals
# ---------------------------------------------------------------------------

class TestMotionVisuals:
    def test_ken_burns_builds_filter(self, sample_ctx):
        from app.effects.motion_visuals import KenBurnsEffect
        effect = KenBurnsEffect()
        result = effect.build(sample_ctx)
        assert any("zoompan" in f for f in result.filters)

    def test_vignette_pulse_builds_filter(self, sample_ctx):
        from app.effects.motion_visuals import VignettePulseEffect
        effect = VignettePulseEffect()
        result = effect.build(sample_ctx)
        assert any("vignette" in f for f in result.filters)

    def test_speed_oscillation_builds_filter(self, sample_ctx):
        from app.effects.motion_visuals import SpeedOscillationEffect
        effect = SpeedOscillationEffect()
        result = effect.build(sample_ctx)
        assert any("setpts" in f for f in result.filters)


# ---------------------------------------------------------------------------
# Skill 3: Celebration Visuals
# ---------------------------------------------------------------------------

class TestCelebrationVisuals:
    def test_screen_flash_burst_filter(self, sample_ctx):
        from app.effects.celebration_visuals import ScreenFlashBurstEffect
        effect = ScreenFlashBurstEffect()
        result = effect.build(sample_ctx)
        assert any("eq=brightness" in f for f in result.filters)

    def test_golden_glow_filter(self, sample_ctx):
        from app.effects.celebration_visuals import GoldenGlowEffect
        effect = GoldenGlowEffect()
        result = effect.build(sample_ctx)
        assert any("colorbalance" in f for f in result.filters)

    def test_score_popup_filter(self, sample_ctx):
        from app.effects.celebration_visuals import ScorePopupEffect
        effect = ScorePopupEffect()
        result = effect.build(sample_ctx)
        assert any("drawtext" in f for f in result.filters)


# ---------------------------------------------------------------------------
# Skill 4: Emotion Visuals
# ---------------------------------------------------------------------------

class TestEmotionVisuals:
    def test_tension_pulse_builds_filter(self, sample_ctx):
        from app.effects.emotion_visuals import TensionPulseEffect
        effect = TensionPulseEffect()
        result = effect.build(sample_ctx)
        assert len(result.filters) >= 2  # brightness + vignette

    def test_joy_bloom_builds_filter(self, sample_ctx):
        from app.effects.emotion_visuals import JoyBloomEffect
        effect = JoyBloomEffect()
        result = effect.build(sample_ctx)
        assert any("colorbalance" in f for f in result.filters)

    def test_shock_freeze_builds_filter(self, sample_ctx):
        from app.effects.emotion_visuals import ShockFreezeEffect
        effect = ShockFreezeEffect()
        result = effect.build(sample_ctx)
        assert any("setpts" in f for f in result.filters)

    def test_heartbreak_builds_filter(self, sample_ctx):
        from app.effects.emotion_visuals import HeartbreakEffect
        effect = HeartbreakEffect()
        result = effect.build(sample_ctx)
        assert any("setpts" in f for f in result.filters)
        assert any("colorbalance" in f for f in result.filters)


# ---------------------------------------------------------------------------
# Skill 7: Style Presets
# ---------------------------------------------------------------------------

class TestStylePresets:
    def test_broadcast_pro_preset(self, sample_ctx):
        from app.effects.style_presets import StylePresetEffect
        sample_ctx.extra_data = {"style_preset": "broadcast_pro"}
        effect = StylePresetEffect()
        result = effect.build(sample_ctx)
        assert len(result.filters) > 0

    def test_dramatic_cinema_preset(self, sample_ctx):
        from app.effects.style_presets import StylePresetEffect
        sample_ctx.extra_data = {"style_preset": "dramatic_cinema"}
        effect = StylePresetEffect()
        result = effect.build(sample_ctx)
        assert any("colorbalance" in f for f in result.filters)

    def test_low_intensity_skips_grain(self, low_intensity_ctx):
        from app.effects.style_presets import StylePresetEffect
        low_intensity_ctx.extra_data = {"style_preset": "dramatic_cinema"}
        effect = StylePresetEffect()
        result = effect.build(low_intensity_ctx)
        assert not any("noise" in f for f in result.filters)

    def test_unknown_preset_falls_back(self, sample_ctx):
        from app.effects.style_presets import StylePresetEffect
        sample_ctx.extra_data = {"style_preset": "nonexistent"}
        effect = StylePresetEffect()
        result = effect.build(sample_ctx)
        # Falls back to broadcast_pro
        assert len(result.filters) > 0


# ---------------------------------------------------------------------------
# Skill 6: Animated Overlays
# ---------------------------------------------------------------------------

class TestAnimatedOverlays:
    def test_score_bug_builds_filter(self, sample_ctx):
        from app.effects.animated_overlays import ScoreBugEffect
        sample_ctx.team_home = "Brazil"
        sample_ctx.team_away = "Argentina"
        sample_ctx.score_home = 2
        sample_ctx.score_away = 1
        effect = ScoreBugEffect()
        result = effect.build(sample_ctx)
        assert any("drawtext" in f for f in result.filters)

    def test_player_nameplate_builds_filter(self, sample_ctx):
        from app.effects.animated_overlays import PlayerNamePlateEffect
        sample_ctx.player_name = "Neymar"
        sample_ctx.player_number = 10
        effect = PlayerNamePlateEffect()
        result = effect.build(sample_ctx)
        assert any("drawbox" in f for f in result.filters)
        assert any("drawtext" in f for f in result.filters)

    def test_timer_overlay_builds_filter(self, sample_ctx):
        from app.effects.animated_overlays import TimerOverlayEffect
        effect = TimerOverlayEffect()
        result = effect.build(sample_ctx)
        assert any("drawtext" in f for f in result.filters)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestEffectRegistry:
    def test_registry_creates_singleton(self):
        from app.effects.registry import get_registry, _registry
        # Force re-creation
        import app.effects.registry as reg_module
        reg_module._registry = None
        r = get_registry()
        assert r is not None

    def test_registry_auto_registers_effects(self):
        from app.effects.registry import get_registry
        import app.effects.registry as reg_module
        reg_module._registry = None
        r = get_registry()
        # Should have registered effects from all skill modules
        assert len(r.all_effects()) > 0

    def test_build_effects_for_clip(self, sample_ctx):
        from app.effects.registry import get_registry
        import app.effects.registry as reg_module
        reg_module._registry = None
        r = get_registry()
        results = r.build_effects_for_clip(sample_ctx)
        # Should return some effect results
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Integration: EditSettings → intensity mapping
# ---------------------------------------------------------------------------

class TestIntensityMapping:
    def test_light_editing_intensity(self):
        from app.renderer.advanced_clip_editor import EditSettings
        settings = EditSettings(speed_ramp=(1.0, 1.05))
        editor = MagicMock()
        editor.settings = settings
        # Import the method from the actual class
        from app.renderer.advanced_clip_editor import AdvancedClipEditor
        editor_cls = AdvancedClipEditor.__new__(AdvancedClipEditor)
        editor_cls.settings = settings
        assert editor_cls._edit_style_to_intensity() == 0.3

    def test_moderate_editing_intensity(self):
        from app.renderer.advanced_clip_editor import EditSettings, AdvancedClipEditor
        settings = EditSettings(speed_ramp=(1.05, 1.10))
        editor = AdvancedClipEditor.__new__(AdvancedClipEditor)
        editor.settings = settings
        assert editor._edit_style_to_intensity() == 0.5

    def test_heavy_editing_intensity(self):
        from app.renderer.advanced_clip_editor import EditSettings, AdvancedClipEditor
        settings = EditSettings(speed_ramp=(1.05, 1.15))
        editor = AdvancedClipEditor.__new__(AdvancedClipEditor)
        editor.settings = settings
        assert editor._edit_style_to_intensity() == 0.8
