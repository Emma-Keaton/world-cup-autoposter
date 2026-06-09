"""Skill 2: Motion Visuals — Flow & movement effects.

Adds continuous motion to clips so reposted footage feels cinematic:
Ken Burns drift, parallax depth, floating overlays, wave distortion,
speed oscillation, and vignette pulse.

Inspired by: Anime.js path-following, GSAP timeline, PixiJS displacement,
Vanta.js WAVES, React Spring oscillation.
"""

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType
from app.effects.easing import ffmpeg_sine_expr, ffmpeg_vignette_expr


class KenBurnsEffect(BaseEffect):
    """Multi-keyframe pan with sinusoidal velocity — cinematic drift."""

    name = "ken_burns"
    label = "Cinematic Ken Burns"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Smooth pan+zoom drift for wide and tactical clips"
    handled_tags = ["zoom_in", "slow_motion"]

    def build(self, ctx: EffectContext) -> EffectResult:
        zoom_start = 1.0 + self.scale(0.08, ctx.intensity)
        zoom_end = 1.0 + self.scale(0.20, ctx.intensity)
        # Pan from left-center to right-center
        x_expr = f"iw/2-(iw/2)*on/{int(ctx.duration * ctx.fps)}*0.15*{ctx.intensity:.2f}"
        y_expr = f"ih/2-(ih/2)*sin(on/{int(ctx.duration * ctx.fps) * 2})*0.05*{ctx.intensity:.2f}"
        z_expr = f"{zoom_start:.3f}+({zoom_end - zoom_start:.3f})*on/{int(ctx.duration * ctx.fps)}"
        total_frames = int(ctx.duration * ctx.fps)
        return EffectResult(
            filters=[
                f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
                f":d={total_frames}:s={ctx.width}x{ctx.height}:fps={ctx.fps}"
            ],
        )


class ParallaxDepthEffect(BaseEffect):
    """Two-layer parallax — background drifts opposite to foreground."""

    name = "parallax_depth"
    label = "Parallax Depth"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Background/foreground counter-movement for depth"
    handled_tags = ["zoom_in"]

    def build(self, ctx: EffectContext) -> EffectResult:
        shift_px = int(self.scale(30, ctx.intensity))
        total_frames = int(ctx.duration * ctx.fps)
        # Slight zoom + pan for parallax-like depth
        x_drift = ffmpeg_sine_expr("on", shift_px, 0.4 / ctx.duration, 0, 0)
        return EffectResult(
            pre_filters=[f"pad={ctx.width + shift_px * 2}:{ctx.height + shift_px * 2}:(ow-iw)/2:(oh-ih)/2"],
            filters=[
                f"crop={ctx.width}:{ctx.height}:'{x_drift}':'ih/2-(oh/2)'",
            ],
        )


class FloatingTextEffect(BaseEffect):
    """Gentle bobbing motion on drawtext overlays — sine-wave oscillation."""

    name = "floating_text"
    label = "Floating Text Overlay"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.FILTER
    description = "Bobbing motion on text overlays"
    handled_tags = ["text_overlay"]

    def build(self, ctx: EffectContext) -> EffectResult:
        amplitude = self.scale(8, ctx.intensity)
        text = ctx.extra_data.get("text", ctx.player_name or "GOAL!")
        y_base = ctx.height - 200
        y_expr = ffmpeg_sine_expr("t", amplitude, 0.8, 0, y_base)
        return EffectResult(
            filters=[
                f"drawtext=text='{text}':fontsize=64:fontcolor=white"
                f":borderw=3:bordercolor=black:x=(w-text_w)/2:y='{y_expr}'"
            ],
        )


class WaveDistortionEffect(BaseEffect):
    """Subtle water/heat ripple via animated displacement mapping."""

    name = "wave_distortion"
    label = "Wave Distortion"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Subtle ripple distortion for celebration/crowd shots"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        amp = int(self.scale(5, ctx.intensity))
        freq = 2 + ctx.intensity * 3
        return EffectResult(
            filters=[
                # Sine-wave horizontal displacement
                f"geq=p('X'+{amp}*sin({freq}*PI*T/10),Y):p(X,Y+{amp}*cos({freq}*PI*T/10))",
            ],
        )


class SpeedOscillationEffect(BaseEffect):
    """Gentle speed variation — subtly speeds up/slows down within range."""

    name = "speed_oscillation"
    label = "Speed Oscillation"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Subtle rhythmic speed variation for build-up play"
    handled_tags = ["speed_ramp"]

    def build(self, ctx: EffectContext) -> EffectResult:
        base = 1.05 + self.scale(0.05, ctx.intensity)
        swing = self.scale(0.05, ctx.intensity)
        # Speed oscillates between (base - swing) and (base + swing)
        expr = f"{base:.3f}+{swing:.3f}*sin(2*PI*T/{max(ctx.duration * 0.4, 0.5):.2f})"
        return EffectResult(filters=[f"setpts=PTS/{expr}"])


class VignettePulseEffect(BaseEffect):
    """Dynamic vignette that tightens on dramatic moments and loosens on calm."""

    name = "vignette_pulse"
    label = "Vignette Pulse"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Pulsing vignette that responds to clip intensity"
    handled_tags = ["dramatic_pause", "slow_motion"]

    def build(self, ctx: EffectContext) -> EffectResult:
        base_angle = 0.3 + self.scale(0.2, ctx.intensity)
        pulse_amp = self.scale(0.1, ctx.intensity)
        angle_expr = ffmpeg_vignette_expr("T", base_angle, pulse_amp, 1.5)
        return EffectResult(filters=[f"vignette=angle='{angle_expr}'"])


# ---------------------------------------------------------------------------
ALL_MOTION_EFFECTS = [
    KenBurnsEffect,
    ParallaxDepthEffect,
    FloatingTextEffect,
    WaveDistortionEffect,
    SpeedOscillationEffect,
    VignettePulseEffect,
]
