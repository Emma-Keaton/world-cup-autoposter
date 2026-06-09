"""Skill 5: Scream Visuals — Audio-reactive effects.

Uses librosa (already a dependency) to drive visual effects that react to
commentator screams, crowd roars, and TTS emphasis.

Inspired by: PixiJS audio-reactive patterns, Three.js per-frame updates,
GSAP scrub (progress-mapped), React Spring velocity preservation.
"""

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType
from app.effects.audio_analyzer import analyze_audio, smooth_envelope


class AudioReactiveZoomEffect(BaseEffect):
    """Zoom level driven by audio RMS energy — louder = closer."""

    name = "audio_reactive_zoom"
    label = "Audio-Reactive Zoom Pulse"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.AUDIO_REACTIVE
    description = "Zoom follows audio volume for commentator screams"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        if not ctx.audio_path:
            return EffectResult()

        analysis = analyze_audio(ctx.audio_path)
        # Build zoompan z expression from RMS envelope
        # Map RMS 0–1 to zoom range 1.0–1.25
        max_zoom = 1.0 + self.scale(0.25, ctx.intensity)
        # Create per-second keyframe expression
        keyframes = []
        fps = ctx.fps
        total_frames = int(ctx.duration * fps)
        for frame in range(total_frames):
            t = frame / fps
            rms = analysis.rms_at_time(t)
            zoom = 1.0 + (max_zoom - 1.0) * rms
            keyframes.append(zoom)

        # Smooth the keyframes (React Spring velocity-preservation pattern)
        smoothed = smooth_envelope(keyframes, smoothing=0.6)
        # Build FFmpeg expression: piecewise linear between keyframes
        # Simplified: use zoompan with time-based lookup
        segments = []
        step = max(total_frames // 60, 1)  # 60 control points max
        for i in range(0, len(smoothed), step):
            segments.append(f"if(lte(on,{i}),{smoothed[i]:.4f}")
        # Fallback to simple sine-modulated expression if too few frames
        if len(segments) < 2:
            expr = f"1+{self.scale(0.15, ctx.intensity):.3f}*0.5*(1+sin(2*PI*2*T))"
        else:
            # Nested if chain
            expr = segments[0]
            for s in segments[1:]:
                expr = expr + "," + s
            expr = expr + "," + str(smoothed[-1]) + ")" * len(segments)

        return EffectResult(
            filters=[
                f"zoompan=z='{expr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":s={ctx.width}x{ctx.height}:fps={ctx.fps}"
            ],
        )


class BassShakeEffect(BaseEffect):
    """Low-frequency energy drives horizontal screen displacement."""

    name = "bass_shake"
    label = "Bass Shake"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.AUDIO_REACTIVE
    description = "Screen shake driven by bass frequencies for crowd roars"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        if not ctx.audio_path:
            return EffectResult()

        analysis = analyze_audio(ctx.audio_path)
        max_amp = int(self.scale(12, ctx.intensity))
        # Build a time-varying shake expression from bass envelope
        # Sample bass at key moments, create a simplified expression
        # Use averaged bass energy to modulate shake amplitude
        peak_bass = max(analysis.bass_envelope) if analysis.bass_envelope else 0.5
        avg_bass = sum(analysis.bass_envelope) / max(len(analysis.bass_envelope), 1)
        bass_ratio = min(peak_bass / max(avg_bass * 2, 0.01), 1.0)
        amp = max_amp * bass_ratio

        # Expression: shake when bass is high, decay when low
        # Simplified: amplitude-modulated sine
        expr = (
            f"if(gt({bass_ratio:.2f},0.3),"
            f"{amp}*sin(15*on)*exp(-3*T/{ctx.duration:.1f}),0)"
        )
        return EffectResult(
            pre_filters=[f"pad={ctx.width + amp * 2}:{ctx.height + amp * 2}:(ow-iw)/2:(oh-ih)/2"],
            filters=[f"crop={ctx.width}:{ctx.height}:'{expr}':'ih/2-(oh/2)'"],
        )


class VolumeGlowEffect(BaseEffect):
    """Audio RMS mapped to vignette intensity + warm color boost."""

    name = "volume_glow"
    label = "Volume Glow"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.AUDIO_REACTIVE
    description = "Audio-driven vignette and warmth for emotional peaks"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        if not ctx.audio_path:
            return EffectResult()

        analysis = analyze_audio(ctx.audio_path)
        avg_rms = sum(analysis.rms_envelope) / max(len(analysis.rms_envelope), 1)
        rms_scale = min(avg_rms * 2, 1.0) * ctx.intensity

        warm_r = self.scale(0.04, rms_scale)
        warm_g = self.scale(0.02, rms_scale)
        vig_angle = 0.2 + self.scale(0.3, rms_scale)

        return EffectResult(
            filters=[
                f"colorbalance=rs={warm_r:.3f}:gs={warm_g:.3f}",
                f"vignette=angle={vig_angle:.2f}",
            ],
        )


class BeatFlashEffect(BaseEffect):
    """Onset-driven brightness spike at each beat/transient."""

    name = "beat_flash"
    label = "Beat Flash"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.AUDIO_REACTIVE
    description = "Brief brightness spike on audio onsets"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        if not ctx.audio_path:
            return EffectResult()

        analysis = analyze_audio(ctx.audio_path)
        flash_amp = self.scale(0.3, ctx.intensity)
        flash_dur = 0.05  # 50ms flash

        # Build enable chain for each onset
        enables = []
        for onset_frame in analysis.onsets[:30]:  # Limit to 30 flashes
            onset_t = onset_frame / analysis.analysis_fps
            enables.append(f"between(T,{onset_t:.3f},{onset_t + flash_dur:.3f})")

        if not enables:
            return EffectResult()

        # Combine with OR
        enable_expr = "+".join(enables)
        brightness_expr = f"if(gt({enable_expr},0),1+{flash_amp:.2f},1)"
        return EffectResult(filters=[f"eq=brightness='{brightness_expr}'"])


class PulsingBorderEffect(BaseEffect):
    """Drawbox border width oscillating with audio amplitude."""

    name = "pulsing_border"
    label = "Pulsing Border"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.AUDIO_REACTIVE
    description = "Team-color border that pulses with audio amplitude"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        max_w = int(self.scale(8, ctx.intensity))
        color = ctx.extra_data.get("border_color", "0x1a4d2e")
        # Oscillate border width with time
        w_expr = f"{max_w}*(0.5+0.5*sin(2*PI*3*T))"
        return EffectResult(
            filters=[
                f"drawbox=x=0:y=0:w=iw:h=ih:t='{w_expr}':c={color}"
            ],
        )


ALL_SCREAM_EFFECTS = [
    AudioReactiveZoomEffect,
    BassShakeEffect,
    VolumeGlowEffect,
    BeatFlashEffect,
    PulsingBorderEffect,
]
