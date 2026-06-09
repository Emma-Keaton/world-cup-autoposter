"""Easing and physics functions adapted from GSAP, Anime.js, React Spring, and Framer Motion.

These produce FFmpeg expression strings or Python keyframe values for
smooth, natural-looking video transitions and animations.
"""

import math
from typing import List, Tuple


# ---------------------------------------------------------------------------
# GSAP-style polynomial easing  (power1–power4, in/out/inOut)
# ---------------------------------------------------------------------------

def power_in(t: float, exponent: int = 2) -> float:
    return t ** exponent


def power_out(t: float, exponent: int = 2) -> float:
    return 1 - (1 - t) ** exponent


def power_in_out(t: float, exponent: int = 2) -> float:
    if t < 0.5:
        return (2 * t) ** exponent / 2
    return 1 - ((-2 * t + 2) ** exponent) / 2


# Convenience aliases matching GSAP naming
power1_in = lambda t: power_in(t, 1)
power1_out = lambda t: power_out(t, 1)
power1_in_out = lambda t: power_in_out(t, 1)
power2_in = lambda t: power_in(t, 2)
power2_out = lambda t: power_out(t, 2)           # GSAP default for 80% of UI
power2_in_out = lambda t: power_in_out(t, 2)
power3_in = lambda t: power_in(t, 3)
power3_out = lambda t: power_out(t, 3)
power3_in_out = lambda t: power_in_out(t, 3)
power4_in = lambda t: power_in(t, 4)
power4_out = lambda t: power_out(t, 4)
power4_in_out = lambda t: power_in_out(t, 4)


# ---------------------------------------------------------------------------
# Exponential easing  (GSAP expo.in / expo.out)
# ---------------------------------------------------------------------------

def expo_in(t: float) -> float:
    return 0 if t == 0 else pow(2, 10 * t - 10)


def expo_out(t: float) -> float:
    return 1 if t == 1 else 1 - pow(2, -10 * t)


def expo_in_out(t: float) -> float:
    if t == 0 or t == 1:
        return t
    if t < 0.5:
        return pow(2, 20 * t - 10) / 2
    return (2 - pow(2, -20 * t + 10)) / 2


# ---------------------------------------------------------------------------
# Back easing  (GSAP back.out with overshoot)
# ---------------------------------------------------------------------------

def back_in(t: float, overshoot: float = 1.70158) -> float:
    s = overshoot
    return t * t * ((s + 1) * t - s)


def back_out(t: float, overshoot: float = 1.70158) -> float:
    s = overshoot
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def back_in_out(t: float, overshoot: float = 1.70158) -> float:
    s = overshoot * 1.525
    if t < 0.5:
        return (2 * t) ** 2 * ((s + 1) * 2 * t - s) / 2
    t = 2 * t - 2
    return (t ** 2 * ((s + 1) * t + s) + 2) / 2


# ---------------------------------------------------------------------------
# Elastic easing  (GSAP elastic.out)
# ---------------------------------------------------------------------------

def elastic_out(t: float, amplitude: float = 1, period: float = 0.3) -> float:
    if t == 0 or t == 1:
        return t
    a = max(amplitude, 1)
    p = period
    s = p / 4
    return a * pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1


# ---------------------------------------------------------------------------
# Bounce easing  (GSAP bounce.out)
# ---------------------------------------------------------------------------

def bounce_out(t: float) -> float:
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


# ---------------------------------------------------------------------------
# Sine easing
# ---------------------------------------------------------------------------

def sine_in(t: float) -> float:
    return 1 - math.cos((t * math.pi) / 2)


def sine_out(t: float) -> float:
    return math.sin((t * math.pi) / 2)


def sine_in_out(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


# ---------------------------------------------------------------------------
# Spring physics  (React Spring / Anime.js)
# ---------------------------------------------------------------------------

def spring_ease(
    t: float,
    mass: float = 1.0,
    tension: float = 170.0,
    friction: float = 26.0,
    velocity: float = 0.0,
    dt: float = 1 / 60,
) -> float:
    """Simulate a spring from 0→1 using Hooke's law with damping.

    Adapted from React Spring's physics model (mass/tension/friction).
    Critical damping: friction_critical = 2 * sqrt(tension * mass).
    """
    position = 0.0
    vel = velocity
    steps = int(t / dt)
    for _ in range(max(steps, 1)):
        spring_force = -tension * (position - 1)
        damping_force = -friction * vel
        acceleration = (spring_force + damping_force) / mass
        vel += acceleration * dt
        position += vel * dt
        if abs(position - 1) < 0.001 and abs(vel) < 0.001:
            return 1.0
    return position


# React Spring config presets
SPRING_GENTLE = dict(mass=1, tension=120, friction=14)
SPRING_DEFAULT = dict(mass=1, tension=170, friction=26)
SPRING_WOBBLY = dict(mass=1, tension=180, friction=12)
SPRING_STIFF = dict(mass=1, tension=210, friction=20)
SPRING_SLOW = dict(mass=1, tension=280, friction=60)
SPRING_MOLASSES = dict(mass=1, tension=280, friction=120)


def critical_damping_ratio(tension: float, mass: float = 1.0, friction: float = 26.0) -> float:
    """Calculate damping ratio (zeta). <1 underdamped, =1 critically damped, >1 overdamped."""
    friction_critical = 2 * math.sqrt(tension * mass)
    return friction / friction_critical


# ---------------------------------------------------------------------------
# Keyframe interpolation — generate N values with an easing function
# ---------------------------------------------------------------------------

def interpolate_keyframes(
    start: float,
    end: float,
    count: int,
    ease_fn=power2_out,
) -> List[float]:
    """Return *count* evenly-spaced samples between start and end,
    shaped by *ease_fn* (a callable 0→1 → 0→1)."""
    return [start + (end - start) * ease_fn(i / max(count - 1, 1)) for i in range(count)]


# ---------------------------------------------------------------------------
# FFmpeg expression helpers
# ---------------------------------------------------------------------------

def ffmpeg_sine_expr(
    variable: str = "t",
    amplitude: float = 10,
    frequency: float = 0.8,
    phase: float = 0,
    offset: float = 0,
) -> str:
    """Return an FFmpeg expression string for a sine-wave oscillation."""
    return f"{offset}+{amplitude}*sin({frequency}*2*PI*{variable}+{phase})"


def ffmpeg_spring_zoom_expr(
    start_zoom: float = 1.0,
    peak_zoom: float = 1.3,
    settle_zoom: float = 1.15,
    punch_frames: int = 6,
    settle_frames: int = 20,
) -> str:
    """Return a zoompan z= expression for a spring-eased zoom punch.

    Fast snap to peak_zoom, then spring-settle to settle_zoom.
    """
    # Build a piecewise expression:
    # if frame < punch_frames:  linear ramp to peak
    # else:  exponential decay from peak toward settle
    return (
        f"if(lte(on,{punch_frames}),"
        f"{start_zoom}+({peak_zoom}-{start_zoom})*on/{punch_frames},"
        f"{settle_zoom}+({peak_zoom}-{settle_zoom})"
        f"*exp(-(on-{punch_frames})/{settle_frames}))"
    )


def ffmpeg_shake_expr(
    variable: str = "x",
    amplitude: float = 8,
    frequency: float = 15,
    decay_rate: float = 3,
    start_frame: int = 0,
    duration_frames: int = 15,
) -> str:
    """Return an FFmpeg expression for decaying screen shake."""
    return (
        f"if(between(on,{start_frame},{start_frame + duration_frames}),"
        f"{amplitude}*sin({frequency}*on)*"
        f"exp(-{decay_rate}*(on-{start_frame})/{duration_frames}),0)"
    )


def ffmpeg_vignette_expr(
    time_var: str = "t",
    base_angle: float = 0.4,
    pulse_amplitude: float = 0.15,
    pulse_frequency: float = 1.5,
) -> str:
    """Return an FFmpeg vignette angle expression with gentle pulsing."""
    return f"{base_angle}+{pulse_amplitude}*sin({pulse_frequency}*2*PI*{time_var})"
