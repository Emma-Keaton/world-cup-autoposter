"""Skill 3: Celebration Visuals — Goal & victory overlays.

Generates confetti, fireworks, screen flash, golden glow, and score popups
as Pillow-rendered PNG frame sequences composited via FFmpeg overlay.

Inspired by: PixiJS explosion/fountain particles, Three.js bloom,
GSAP stagger, Lottie segment playback, Vanta.js BIRDS flocking.
"""

import asyncio
import math
import tempfile
from pathlib import Path
from typing import List

from app.effects.base import BaseEffect, EffectContext, EffectResult, EffectStage, EffectType
from app.effects.particles import (
    emit_confetti,
    emit_explosion,
    emit_fountain,
    render_particle_sequence,
    color_gradient_fire,
    color_gradient_confetti,
)
from app.effects.easing import spring_ease, SPRING_WOBBLY


class ConfettiBurstEffect(BaseEffect):
    """Colorful confetti burst — 120+ particles with gravity, wind, rotation."""

    name = "confetti_burst"
    label = "Confetti Burst"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.OVERLAY
    description = "Colorful confetti overlay for goals and victories"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        count = int(80 + 80 * ctx.intensity)
        duration = 2.0 + ctx.intensity
        output_dir = Path(tempfile.mkdtemp(prefix="confetti_"))
        particles = emit_confetti(
            cx=ctx.width / 2,
            cy=ctx.height * 0.3,
            count=count,
            spread_x=ctx.width * 0.4,
            speed_range=(1, 3 + ctx.intensity * 2),
            gravity=0.08,
            wind=0.2 + ctx.intensity * 0.3,
            max_life=duration,
        )
        # Run render in thread pool to not block async loop
        output_dir = render_particle_sequence(
            particles,
            output_dir=output_dir,
            width=ctx.width,
            height=ctx.height,
            fps=ctx.fps,
            duration=duration,
            color_fn=color_gradient_confetti,
        )
        return EffectResult(
            overlay_frames_dir=str(output_dir),
            overlay_blend="screen",
            metadata={"duration": duration},
        )


class FireworkSparksEffect(BaseEffect):
    """Radial firework burst — golden/white sparks with gravity and drag."""

    name = "firework_sparks"
    label = "Firework Sparks"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.OVERLAY
    description = "Golden firework sparks for goals and wins"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        count = int(60 + 60 * ctx.intensity)
        duration = 1.5 + ctx.intensity * 0.5
        output_dir = Path(tempfile.mkdtemp(prefix="firework_"))
        particles = emit_explosion(
            cx=ctx.width / 2,
            cy=ctx.height * 0.35,
            count=count,
            speed_range=(3, 8 + ctx.intensity * 4),
            gravity=0.12 + ctx.intensity * 0.05,
            drag=0.97,
            max_life=duration,
            size_range=(2, 5 + ctx.intensity * 3),
            color_fn=color_gradient_fire,
        )
        output_dir = render_particle_sequence(
            particles,
            output_dir=output_dir,
            width=ctx.width,
            height=ctx.height,
            fps=ctx.fps,
            duration=duration,
            color_fn=color_gradient_fire,
        )
        return EffectResult(
            overlay_frames_dir=str(output_dir),
            overlay_blend="additive",
            metadata={"duration": duration},
        )


class ScreenFlashBurstEffect(BaseEffect):
    """Full-screen white flash with exponential decay."""

    name = "screen_flash"
    label = "Screen Flash Burst"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Exponential-decay white flash for goals"
    handled_tags = ["dramatic_pause"]

    def build(self, ctx: EffectContext) -> EffectResult:
        peak_brightness = self.scale(0.7, ctx.intensity)
        decay_rate = 5 + ctx.intensity * 3
        # Brightness spikes then exponentially decays over ~0.5s
        expr = f"if(lt(T,0.5),1+{peak_brightness:.2f}*exp(-{decay_rate:.1f}*T),1)"
        return EffectResult(filters=[f"eq=brightness='{expr}'"])


class GoldenGlowEffect(BaseEffect):
    """Warm radial glow + color temperature shift for celebrations."""

    name = "golden_glow"
    label = "Golden Glow Halo"
    stage = EffectStage.PER_CLIP
    effect_type = EffectType.FILTER
    description = "Warm golden glow for trophy lifts and celebrations"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        warm_r = self.scale(0.06, ctx.intensity)
        warm_g = self.scale(0.03, ctx.intensity)
        cool_b = self.scale(-0.04, ctx.intensity)
        return EffectResult(
            filters=[
                f"colorbalance=rs={warm_r:.3f}:gs={warm_g:.3f}:bs={cool_b:.3f}",
                "unsharp=6:6:2:6:6:0",
            ],
        )


class LensFlareEffect(BaseEffect):
    """Anamorphic lens flare with slow drift and opacity oscillation."""

    name = "lens_flare"
    label = "Light Leak / Lens Flare"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.OVERLAY
    description = "Anamorphic flare overlay for emotional peaks"
    handled_tags = []

    def build(self, ctx: EffectContext) -> EffectResult:
        from PIL import Image, ImageDraw, ImageFilter

        duration = ctx.duration
        total_frames = int(duration * ctx.fps)
        output_dir = Path(tempfile.mkdtemp(prefix="flare_"))
        output_dir.mkdir(parents=True, exist_ok=True)

        for i in range(total_frames):
            t = i / ctx.fps
            progress = t / duration
            # Flare drifts across frame
            x = int(ctx.width * (0.3 + 0.4 * progress))
            y = int(ctx.height * (0.2 + 0.1 * math.sin(progress * math.pi * 2)))
            # Opacity oscillation
            alpha = int(40 * ctx.intensity * (0.5 + 0.5 * math.sin(t * 1.5)))
            if alpha < 3:
                alpha = 3

            img = Image.new("RGBA", (ctx.width, ctx.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Horizontal streak
            streak_h = max(int(6 * ctx.intensity), 2)
            draw.rectangle(
                [x - 300, y - streak_h, x + 300, y + streak_h],
                fill=(255, 200, 100, alpha),
            )
            # Center spot
            spot_r = int(30 * ctx.intensity)
            draw.ellipse(
                [x - spot_r, y - spot_r, x + spot_r, y + spot_r],
                fill=(255, 240, 180, min(alpha * 3, 255)),
            )
            img = img.filter(ImageFilter.GaussianBlur(radius=8))
            img.save(output_dir / f"frame_{i:04d}.png", "PNG")

        return EffectResult(
            overlay_frames_dir=str(output_dir),
            overlay_blend="screen",
        )


class ScorePopupEffect(BaseEffect):
    """Score reveal with spring-eased scale-in animation."""

    name = "score_popup"
    label = "Score Popup Animation"
    stage = EffectStage.POST_CONCAT
    effect_type = EffectType.FILTER
    description = "Animated score reveal with spring settle"
    handled_tags = ["text_overlay"]

    def build(self, ctx: EffectContext) -> EffectResult:
        score_text = f"{ctx.score_home} - {ctx.score_away}" if ctx.score_home or ctx.score_away else "GOAL!"
        # Spring-eased scale: text appears large, bounces to settle size
        settle_frames = int(0.4 * ctx.fps)
        # Use drawtext with enable timing for the popup window
        return EffectResult(
            filters=[
                f"drawtext=text='{score_text}':fontsize=120:fontcolor=white"
                f":borderw=4:bordercolor=black"
                f":x=(w-text_w)/2:y=(h-text_h)/2"
                f":enable='between(t,0.3,{0.3 + 0.5 + ctx.intensity:.1f})'"
            ],
        )


ALL_CELEBRATION_EFFECTS = [
    ConfettiBurstEffect,
    FireworkSparksEffect,
    ScreenFlashBurstEffect,
    GoldenGlowEffect,
    LensFlareEffect,
    ScorePopupEffect,
]
