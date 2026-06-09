"""Particle system engine — generates overlay frame sequences with Pillow.

Ported math from PixiJS, Three.js, and Vanta.js particle systems.
Renders particles as PNG frames composited via FFmpeg overlay filter.
"""

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Particle data
# ---------------------------------------------------------------------------

@dataclass
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 1.0
    max_life: float = 1.0
    size: float = 4.0
    rotation: float = 0.0
    rotation_speed: float = 0.0
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    gravity: float = 0.0
    drag: float = 0.99
    wind: float = 0.0

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def life_ratio(self) -> float:
        return max(self.life / self.max_life, 0.0)


# ---------------------------------------------------------------------------
# Color lifecycle helpers  (from PixiJS fire/explosion patterns)
# ---------------------------------------------------------------------------

def color_gradient_fire(t: float) -> Tuple[int, int, int]:
    """Yellow → orange → red → black, based on life ratio t (1=fresh, 0=dead)."""
    if t > 0.7:
        r = 255
        g = int(255 * ((t - 0.7) / 0.3))
        b = 0
    elif t > 0.4:
        r = 255
        g = int(165 * ((t - 0.4) / 0.3))
        b = 0
    elif t > 0.1:
        r = int(255 * ((t - 0.1) / 0.3))
        g = 0
        b = 0
    else:
        v = int(80 * (t / 0.1))
        r = v
        g = 0
        b = 0
    return (r, g, b)


def color_gradient_confetti(t: float, base_hue: float = 0.0) -> Tuple[int, int, int]:
    """Cycling bright colors that fade as life depletes."""
    hue = (base_hue + (1 - t) * 120) % 360
    saturation = 1.0
    value = t
    # HSV to RGB
    c = value * saturation
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = value - c
    if hue < 60:
        r, g, b = c, x, 0
    elif hue < 120:
        r, g, b = x, c, 0
    elif hue < 180:
        r, g, b = 0, c, x
    elif hue < 240:
        r, g, b = 0, x, c
    elif hue < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


# ---------------------------------------------------------------------------
# Emitter patterns  (from PixiJS particle_builder)
# ---------------------------------------------------------------------------

def emit_explosion(
    cx: float,
    cy: float,
    count: int = 80,
    speed_range: Tuple[float, float] = (3, 10),
    gravity: float = 0.15,
    drag: float = 0.97,
    max_life: float = 1.5,
    size_range: Tuple[float, float] = (3, 8),
    color_fn=color_gradient_fire,
) -> List[Particle]:
    """Radial burst from a center point (PixiJS explosion pattern)."""
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        life = random.uniform(max_life * 0.5, max_life)
        p = Particle(
            x=cx,
            y=cy,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            life=life,
            max_life=life,
            size=random.uniform(*size_range),
            gravity=gravity,
            drag=drag,
            rotation=random.uniform(0, 360),
            rotation_speed=random.uniform(-5, 5),
        )
        rgb = color_fn(1.0)
        p.color = (*rgb, 255)
        particles.append(p)
    return particles


def emit_fountain(
    cx: float,
    cy: float,
    count: int = 50,
    spread: float = 0.5,
    speed_range: Tuple[float, float] = (5, 12),
    gravity: float = 0.2,
    drag: float = 0.98,
    max_life: float = 2.0,
    size_range: Tuple[float, float] = (2, 6),
    color_fn=color_gradient_fire,
) -> List[Particle]:
    """Upward spray from a point (PixiJS fountain pattern)."""
    particles = []
    for _ in range(count):
        angle = -math.pi / 2 + random.uniform(-spread, spread)
        speed = random.uniform(*speed_range)
        life = random.uniform(max_life * 0.6, max_life)
        p = Particle(
            x=cx + random.uniform(-5, 5),
            y=cy,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            life=life,
            max_life=life,
            size=random.uniform(*size_range),
            gravity=gravity,
            drag=drag,
        )
        rgb = color_fn(1.0)
        p.color = (*rgb, 255)
        particles.append(p)
    return particles


def emit_confetti(
    cx: float,
    cy: float,
    count: int = 120,
    spread_x: float = 400,
    speed_range: Tuple[float, float] = (1, 4),
    gravity: float = 0.08,
    wind: float = 0.3,
    drag: float = 0.995,
    max_life: float = 3.0,
    size_range: Tuple[float, float] = (4, 10),
) -> List[Particle]:
    """Confetti burst — colorful rectangles falling from above (celebration)."""
    particles = []
    for i in range(count):
        life = random.uniform(max_life * 0.5, max_life)
        base_hue = random.uniform(0, 360)
        p = Particle(
            x=cx + random.uniform(-spread_x, spread_x),
            y=cy - random.uniform(0, 200),
            vx=random.uniform(-speed_range[1], speed_range[1]),
            vy=random.uniform(*speed_range),
            life=life,
            max_life=life,
            size=random.uniform(*size_range),
            gravity=gravity,
            drag=drag,
            wind=random.uniform(-wind, wind),
            rotation=random.uniform(0, 360),
            rotation_speed=random.uniform(-10, 10),
        )
        rgb = color_gradient_confetti(1.0, base_hue)
        p.color = (*rgb, 255)
        particles.append(p)
    return particles


# ---------------------------------------------------------------------------
# Simulation step
# ---------------------------------------------------------------------------

def step_particles(particles: List[Particle], dt: float = 1 / 30) -> List[Particle]:
    """Advance all particles by dt seconds. Returns only alive particles."""
    alive = []
    for p in particles:
        p.vy += p.gravity
        p.vx += p.wind * dt
        p.vx *= p.drag
        p.vy *= p.drag
        p.x += p.vx
        p.y += p.vy
        p.rotation += p.rotation_speed
        p.life -= dt
        if p.alive:
            alive.append(p)
    return alive


# ---------------------------------------------------------------------------
# Rendering to PNG frames
# ---------------------------------------------------------------------------

def render_particle_frame(
    particles: List[Particle],
    width: int = 1080,
    height: int = 1920,
    color_fn=None,
) -> Image.Image:
    """Render current particle state to a transparent RGBA Pillow image."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for p in particles:
        alpha = int(255 * min(p.life_ratio, 1.0))
        if alpha < 5:
            continue
        if color_fn:
            rgb = color_fn(p.life_ratio)
            color = (*rgb, alpha)
        else:
            color = (p.color[0], p.color[1], p.color[2], alpha)
        half = p.size / 2
        x0 = p.x - half
        y0 = p.y - half
        x1 = p.x + half
        y1 = p.y + half
        draw.rectangle([x0, y0, x1, y1], fill=color)
    return img


def render_particle_sequence(
    particles: List[Particle],
    output_dir: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    duration: float = 2.0,
    color_fn=None,
) -> Path:
    """Simulate and render a full particle sequence to PNG frames.

    Returns the output directory containing frame_0000.png, frame_0001.png, ...
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dt = 1 / fps
    total_frames = int(duration * fps)
    current = particles
    for i in range(total_frames):
        current = step_particles(current, dt)
        frame = render_particle_frame(current, width, height, color_fn)
        frame_path = output_dir / f"frame_{i:04d}.png"
        frame.save(frame_path, "PNG")
    return output_dir
