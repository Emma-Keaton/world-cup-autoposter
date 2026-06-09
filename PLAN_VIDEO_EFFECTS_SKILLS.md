# Video Effects Skills Plan — World Cup Autoposter

## What We're Working With

### Current Pipeline (9 stages)
Your autoposter processes videos entirely via **FFmpeg subprocess calls** — no Python video library is used for compositing. The pipeline:

1. **ClipSequencePlanner** — Plans 6-12 visual moments with narrative roles (hook, setup, build, climax, resolution, payoff) and suggests effects like `zoom_in`, `slow_motion`, `dramatic_pause`, `freeze_frame`, etc.
2. **TTSEngine** — Edge-TTS voiceover
3. **SubtitleGenerator** — faster-whisper word-level subtitles (ASS format)
4. **YouTubeDownloader** — yt-dlp source acquisition
5. **SmartClipAssembler** — Maps planned clips to source files
6. **AdvancedClipEditor** — Per-clip FFmpeg filter chain (speed ramp, zoom, color grade, unsharp) + xfade concatenation
7. **EnhancedVideoRenderer** — Platform-optimized encoding (YouTube Shorts, Reels, TikTok)
8. **CopyrightSafetyChecker** — Fair use scoring + audio/visual fingerprinting
9. **ThumbnailCreator** — Image-based thumbnails

**Key gap:** The `ClipPlan.effects` list defines ~10 effect types, but only 4 are actually implemented (`speed_ramp`, `zoom`, `color_grade`, `sharpness`). The rest are dead slots.

### Claude Design Skills — What We Can Adapt

The cloned repo contains **22 web animation/motion graphics skills**. We studied all of them. The key insight: these are all **web/JS** libraries (GSAP, Anime.js, Three.js, PixiJS, Framer Motion, Lottie, Rive, Vanta.js, etc.), but their **patterns, algorithms, and mathematical models** translate directly to FFmpeg filter chains and Python video processing.

---

## The Plan: 7 Video Effect Skills for the Autoposter

Each skill maps to a Python module + FFmpeg filter chain system that slots into the existing pipeline at **Stage 6** (per-clip processing) and between **Stages 6-7** (post-concatenation overlays).

---

### Skill 1: ⚡ Shot Visuals — Impact & Camera Effects

**Source inspiration:** GSAP easing/scrub patterns + PixiJS displacement/chromatic-aberration shaders + Three.js bloom post-processing

**What it does:** Adds "shot" impact effects to key moments — goals, saves, fouls, red cards. Makes the footage feel alive without changing the underlying video content.

**Effects included:**
| Effect | FFmpeg Implementation | When Applied |
|--------|----------------------|-------------|
| **Impact zoom punch** | `zoompan` with spring-eased curve (fast snap in, slow settle out) — adapted from React Spring critical damping formula | Goals, big saves |
| **Screen shake** | Random `x`/`y` translation oscillation via `sendcmd` + sine wave with decay envelope | Hard shots, collisions |
| **Chromatic aberration flash** | Custom `geq` filter splitting R/B channels with offset proportional to impact intensity, fading over 0.3s | Red cards, penalties |
| **Rapid flash/strobe** | `eq=brightness` pulsing between 1.0 → 1.8 → 1.0 in 0.1s cycles, 3-4 pulses | Dramatic moments |
| **Speed ramp with snap** | `setpts` with exponential ease-in followed by hard cut to normal speed | Fast breaks, counter-attacks |
| **Directional motion blur** | `minterpolate` + `tblend` for directional streak blur on fast movement | Quick passes, sprints |

**Math adapted from skills:**
- Spring easing: `friction = 2 * sqrt(tension * mass)` for critically-damped zoom settle (from React Spring)
- GSAP `expo.out` curve: `value = 1 - pow(2, -10 * t)` for punch-in timing
- PixiJS chromatic aberration: channel offset = `uAmount * sin(time * frequency)` with exponential decay

---

### Skill 2: 🎬 Motion Visuals — Flow & Movement Effects

**Source inspiration:** Anime.js path-following + GSAP timeline sequencing + PixiJS displacement waves + Vanta.js WAVES/NET effects

**What it does:** Adds continuous motion and flow to clips that might otherwise look static — makes the video feel cinematic and dynamic, not like a raw repost.

**Effects included:**
| Effect | FFmpeg Implementation | When Applied |
|--------|----------------------|-------------|
| **Cinematic Ken Burns** | `zoompan` with multi-keyframe pan path (start position → drift → end position), sinusoidal velocity curve | All wide/tactical clips |
| **Parallax depth layers** | Two-pass: background slight zoom + foreground slight counter-zoom via crop offset, creates depth illusion | Stadium/aerial shots |
| **Floating text follow** | `drawtext` with `x`/`y` expressions using `sin(t*0.5)*10` for gentle bobbing on player names, scores | Lower-thirds, name plates |
| **Wave distortion overlay** | `displacement` filter with animated noise source — subtle water/heat ripple effect | Celebration crowd shots |
| **Smooth speed oscillation** | `setpts` with sine-modulated speed curve (subtly speeds up/slows down within 1.05x-1.15x range) | Build-up play sequences |
| **Vignette pulse** | Dynamic vignette that tightens on dramatic moments and loosens on calm passages — `geq` radial gradient with time-varying radius | Throughout, intensity-mapped |

**Math adapted from skills:**
- Anime.js spring easing: `spring(mass=1, stiffness=120, damping=14)` → gentle oscillation curves for Ken Burns drift
- GSAP scrub pattern: progress-mapped intensity (`effect_strength = clip_progress * max_intensity`) for vignette pulse
- Vanta.js sine-wave oscillation: `translate.y = sin(time * 0.8) * amplitude` for floating text
- PixiJS displacement wave: Perlin noise texture with `scale` and `speed` parameters for subtle ripple

---

### Skill 3: 🎉 Celebration Visuals — Goal & Victory Effects

**Source inspiration:** PixiJS explosion/fountain particle systems + Three.js InstancedMesh particles + Vanta.js BIRDS flocking + GSAP stagger + Lottie segment playback

**What it does:** Generates celebration overlays — confetti, sparks, flares, screen bursts — for goals, wins, and triumphant moments. These are **rendered as transparent PNG sequences or animated overlays** composited onto the video via FFmpeg `overlay` filter.

**Effects included:**
| Effect | Implementation | When Applied |
|--------|---------------|-------------|
| **Confetti burst** | Python + Pillow generates PNG frame sequence: 200+ particles with gravity, wind drift, rotation, color lifecycle (bright → fade). Composited via FFmpeg `overlay` with alpha | Goals |
| **Firework sparks** | Radial particle emission from point, golden/white color gradient (PixiJS fire pattern: yellow→orange→red→black mapped to life ratio), gravity + drag | Goals, wins |
| **Screen flash burst** | Full-screen white flash with exponential decay (`alpha = e^(-5t)`), 0.5s duration | Goals, penalties scored |
| **Golden glow halo** | Radial gradient overlay (center bright, edge fade) with warm color temp shift — `geq` filter + `colorbalance` | Trophy lifts, celebrations |
| **Flare/light leak** | Anamorphic lens flare PNG overlay with slow drift, opacity oscillation via `sin(t)` | Celebrations, emotional peaks |
| **Score popup animation** | `drawtext` with scale-in effect (large → settle) using `zoompan` on text plane + spring easing | Score reveals |

**Math adapted from skills:**
- PixiJS explosion burst: radial emission `angle = random(0, 2π), speed = random(2, 8)`, with gravity `vy += 0.1` and drag `v *= 0.98`
- PixiJS fire color gradient: `t = particle.life / particle.max_life` → `color = lerp(yellow, orange, t)` → `lerp(orange, red, t-0.5)`
- GSAP stagger from center: particles spawn with delay based on distance from center
- Three.js bloom: overlay with `blend=additive` for glow compositing
- React Spring wobbly preset (180/12): slightly bouncy score popup settle

---

### Skill 4: 😤 Emotion Visuals — Feeling & Intensity Effects

**Source inspiration:** Framer Motion variant state machine + React Spring damping models + GSAP ease curves + Lottie segment playback + PixiJS filters (vignette, CRT, glow)

**What it does:** Adds visual intensity that matches the emotional tone — tension, anger, joy, heartbreak. The emotion is inferred from the `ClipPlan.narrative_role` and `visual_type`.

**Effects included:**
| Effect | FFmpeg Implementation | When Applied |
|--------|----------------------|-------------|
| **Tension pulse** | Slow brightness oscillation (`eq=brightness=1+0.15*sin(t*3)`) + tightening vignette + slight desaturation | Build-up, pre-goal tension |
| **Anger intensify** | Red color channel boost (`colorbalance=rs=0.1`), high-contrast push (`eq=contrast=1.3`), slight shake | Fouls, red cards, arguments |
| **Heartbreak slow-mo** | `setpts=2.0*PTS` with slight blur (`boxblur=2`) + cold blue tint (`colorbalance=bs=0.05`) + rain-like noise overlay | Losses, missed chances, eliminations |
| **Joy bloom** | Warm color shift (`colorbalance=rs=0.03:gs=0.02`), slight glow (`unsharp=6:6:2`), brightness lift | Goals, wins, celebrations |
| **Shock freeze-frame** | `setpts=N/FRAME_RATE/TB` to hold a single frame for 0.5s, then snap back with spring ease | Unexpected moments, upsets |
| **Crowd energy wave** | Subtle hue rotation cycling (`hue="H=2*sin(t*2)"`) + slight saturation boost on crowd shots | Crowd reactions, stadium shots |

**Math adapted from skills:**
- Framer Motion variant state machine: `idle → tension → peak → release → idle` with per-state effect parameters
- React Spring gentle preset (120/14): tension pulse frequency mapped to spring oscillation
- GSAP `back.out(1.7)` easing: slight overshoot on shock freeze-frame return
- PixiJS vignette shader: `smoothstep(center, edge, dist)` with time-varying edge radius
- Lottie segment playback: play tension animation segment during build-up, joy segment during payoff

---

### Skill 5: 🔊 Scream Visuals — Audio-Reactive Effects

**Source inspiration:** PixiJS audio-reactive patterns + Three.js InstancedMesh per-frame updates + GSAP scrub (progress-mapped) + React Spring velocity preservation

**What it does:** Uses the existing `faster-whisper` transcript timing + `librosa` audio analysis (already in the project) to drive visual effects that react to commentator screams, crowd roars, and TTS emphasis points.

**Effects included:**
| Effect | Implementation | When Applied |
|--------|---------------|-------------|
| **Audio-reactive zoom pulse** | `librosa` extracts RMS energy per frame → map to `zoompan` zoom level (louder = closer), with spring smoothing | Commentator screams |
| **Bass shake** | Low-frequency energy from `librosa` spectral analysis → horizontal displacement amplitude for screen shake | Crowd roars, drums |
| **Volume glow** | Audio RMS mapped to vignette intensity + warm color boost — louder = more glow | Emotional peaks in voiceover |
| **Beat flash** | Onset detection via `librosa.onset_detect` → trigger 2-frame brightness spike at each beat | Music-driven highlights |
| **Waveform lower-third** | `drawtext` + Python-generated waveform PNG overlay (from audio envelope), animated across bottom 10% of frame | During TTS narration |
| **Pulsing border** | `drawbox` with border width oscillating with audio amplitude, team-color border | Throughout highlight clips |

**Math adapted from skills:**
- GSAP scrub pattern: audio amplitude (0-1) → effect intensity, with `scrub: 0.5` smoothing equivalent (exponential moving average)
- React Spring velocity preservation: `current_velocity = 0.8 * prev_velocity + 0.2 * new_reading` for smooth audio-reactive transitions
- Three.js per-frame matrix update: update zoom/shake parameters every frame based on audio buffer
- PixiJS color tint by life: map audio energy to color warmth (low energy = neutral, high energy = warm)

---

### Skill 6: 🏆 Animated Overlays — Data-Driven Graphics

**Source inspiration:** Rive ViewModel data binding + Lottie segment playback + GSAP timeline sequencing + Anime.js stagger + React Spring trail cascade

**What it does:** Generates animated lower-thirds, score bugs, stat bars, player cards, and tournament brackets that are **data-driven** (team names, scores, player stats) and **animated in/out** with professional timing.

**Overlay types:**
| Overlay | Implementation | Animation |
|---------|---------------|-----------|
| **Score bug** | Python + Pillow generates each frame: team crest + name + score. Slide-in from left with spring ease, hold, slide-out right | GSAP timeline: `enter(0.3s) → hold → exit(0.3s)` |
| **Player name plate** | Semi-transparent bar with player name + number + flag. Stagger-in: bar slides in first, then text fades in 0.1s later | Anime.js stagger: bar first, text second |
| **Stat comparison bar** | Horizontal bars animated from 0 to value width. React Spring trail cascade: each bar starts after previous with 0.15s delay | React Spring `useTrail` pattern |
| **Tournament bracket** | PNG overlay of bracket tree, with match results highlighted in sequence | GSAP timeline labels: `groupStage → r16 → qf → sf → final` |
| **Animated subtitle style** | ASS subtitle generator enhancement: word-by-word color highlight synced to TTS timing, bold current word | Lottie segment: play highlight animation per word |
| **Timer/clock overlay** | `drawtext` with `timecode` format, counting up/down, monospace font | Continuous, fade-in at start |

**Math adapted from skills:**
- Rive ViewModel: bind Python data (team, score, player) to overlay template properties
- GSAP timeline position parameter: `"-=0.1"` for overlapping enter/exit animations
- Anime.js stagger from center: stats animate from center bar outward
- React Spring trail: each overlay element follows previous with spring delay

---

### Skill 7: 🎨 Style Presets — Signature Look Packages

**Source inspiration:** Modern Web Design trends + PixiJS ColorMatrixFilter presets + Three.js PBR material system + Vanta.js color themes + Blender texture baking

**What it does:** Provides one-click visual style presets that apply a coordinated set of effects across the entire video. Each preset creates a distinctive "look" so reposted videos don't look identical to the source.

**Presets:**
| Preset | Effect Chain | Use Case |
|--------|-------------|----------|
| **Broadcast Pro** | Subtle vignette + warm color grade + slight unsharp + thin letterbox bars (2.35:1 crop with padding) | Standard highlight videos |
| **Dramatic Cinema** | Cool teal shadows + warm orange highlights (teal-orange split tone) + heavy vignette + film grain overlay + 24fps look (`minterpolate`) | Epic comeback stories |
| **Neon Night** | Boosted saturation + glow on brights (`unsharp` additive) + dark crushed blacks + chromatic edge highlights | Night matches, indoor |
| **Vintage Film** | Kodachrome color matrix (`hue=s=0.8,eq=saturation=0.7:contrast=1.1`) + grain + slight vertical jitter + 4:3 safe area markers | Retro/throwback clips |
| **High Energy** | Slight speed ramp (1.1x avg) + saturation boost + contrast pop + rapid-cut transitions (0.3s xfade) + bass-reactive border | TikTok/Reels format |
| **Clean Minimal** | Neutral grade + thin white border + clean sans-serif text + subtle shadow on overlays | Professional/presentation |

**Math adapted from skills:**
- PixiJS ColorMatrixFilter: `sepia`, `kodachrome`, `technicolor`, `polaroid`, `vintage` preset matrices → translate to FFmpeg `colorchannelmixer` + `eq` filter chains
- Three.js PBR roughness/metalness: translate to contrast/saturation/dark crush parameters
- Vanta.js `setOptions()`: runtime preset switching based on clip context
- Blender texture baking: complex multi-filter looks baked to a single LUT `.cube` file for one-pass application

---

## Architecture: How It All Fits Together

```
┌──────────────────────────────────────────────────────────┐
│                   EXISTING PIPELINE                       │
│                                                          │
│  1. ClipSequencePlanner                                  │
│     └── NOW OUTPUTS: effect_profile per clip             │
│         (shot_type, emotion, intensity, style_preset)    │
│                                                          │
│  2-5. TTS + Subs + Download + Assemble                   │
│         (unchanged)                                      │
│                                                          │
│  6. AdvancedClipEditor  ←──── ALL 7 SKILLS INJECT HERE  │
│     ├── Per-clip processing:                             │
│     │   ├── Skill 1: Shot Visuals (zoom punch, shake)    │
│     │   ├── Skill 2: Motion Visuals (Ken Burns, drift)   │
│     │   ├── Skill 4: Emotion Visuals (tint, pulse)       │
│     │   └── Skill 7: Style Preset (color grade chain)    │
│     │                                                    │
│     ├── Post-concatenation overlays:                     │
│     │   ├── Skill 3: Celebration Visuals (confetti etc)  │
│     │   ├── Skill 5: Scream Visuals (audio-reactive)     │
│     │   └── Skill 6: Animated Overlays (scores, names)   │
│     │                                                    │
│     └── Output: enhanced video with all effects          │
│                                                          │
│  7-9. Render + Copyright + Thumbnail                     │
│         (unchanged)                                      │
└──────────────────────────────────────────────────────────┘
```

### New Files to Create

```
app/
├── effects/                          ← NEW MODULE
│   ├── __init__.py
│   ├── registry.py                   ← Effect registry & loader
│   ├── base.py                       ← Base Effect class
│   ├── shot_visuals.py              ← Skill 1
│   ├── motion_visuals.py            ← Skill 2
│   ├── celebration_visuals.py       ← Skill 3
│   ├── emotion_visuals.py           ← Skill 4
│   ├── scream_visuals.py            ← Skill 5
│   ├── animated_overlays.py         ← Skill 6
│   ├── style_presets.py             ← Skill 7
│   ├── particles.py                 ← Shared particle system (Pillow-based)
│   ├── audio_analyzer.py            ← Shared audio analysis (librosa-based)
│   ├── easing.py                    ← Easing/physics functions (adapted from GSAP/React Spring/Anime.js)
│   └── assets/                      ← Pre-rendered overlay frames
│       ├── confetti/
│       ├── flares/
│       ├── light_leaks/
│       └── grain/
```

### Key Design Decisions

1. **Everything stays FFmpeg-based** — No new video processing dependencies. All effects compile to FFmpeg filter chains or Pillow-generated overlay frames composited via FFmpeg `overlay`. This matches your existing architecture perfectly.

2. **Effects are intensity-scaled** — Each effect accepts an `intensity` parameter (0.0-1.0). Light editing = subtle effects, heavy editing = dramatic effects. This maps to your existing `edit_style` ("light" → 0.3, "moderate" → 0.6, "heavy_editing" → 1.0).

3. **The `ClipPlan.effects` list gets wired up** — Currently dead slots like `slow_motion`, `dramatic_pause`, `freeze_frame` will finally be implemented by the new skills.

4. **Particle effects use Pillow, not JS** — PixiJS/Three.js particle math is ported to Python + Pillow for generating overlay frame sequences. No JS runtime needed.

5. **Audio-reactive effects use librosa** — Already a dependency. No new packages required.

6. **Easing functions are pure Python** — The mathematical easing curves from GSAP (`power2.out`, `expo.out`, `back.out`), React Spring (`spring(mass, tension, friction)`), and Anime.js (`spring()`, `cubicBezier()`) are implemented as Python functions that output FFmpeg expression strings or keyframe interpolation values.

---

## New Dependencies Required

| Package | Why | Already in project? |
|---------|-----|-------------------|
| None! | All effects use FFmpeg + Pillow + librosa + numpy (all existing) | ✅ |

---

## Implementation Order (Recommended)

1. **`easing.py`** — Foundation. All skills depend on these math functions.
2. **`base.py` + `registry.py`** — Effect base class and registration system.
3. **`particles.py`** — Shared particle engine for Skills 3 & 5.
4. **`audio_analyzer.py`** — Shared audio analysis for Skill 5.
5. **Skill 1: `shot_visuals.py`** — Highest impact, fewest dependencies.
6. **Skill 4: `emotion_visuals.py`** — Second highest impact, builds on easing.
7. **Skill 2: `motion_visuals.py`** — Ken Burns + parallax, very common need.
8. **Skill 7: `style_presets.py`** — One-click looks, combines effects from 1/2/4.
9. **Skill 6: `animated_overlays.py`** — Data-driven graphics, most complex.
10. **Skill 3: `celebration_visuals.py`** — Particle-heavy, depends on particles.py.
11. **Skill 5: `scream_visuals.py`** — Audio-reactive, depends on audio_analyzer.py.
12. **Wire up to `AdvancedClipEditor`** — Connect all skills to the pipeline.
13. **Wire up to `ClipSequencePlanner`** — Auto-select effects based on clip analysis.

---

## Risk & Considerations

- **Performance:** Multiple FFmpeg passes are slow. We should combine effects into single filter graphs where possible. The `registry.py` will batch compatible effects into one pass.
- **Render time on free tier:** Render.com free tier has limited CPU. Heavy particle effects (200+ confetti frames) add ~10-15s per clip. We should pre-render common assets.
- **Subtlety is key:** As you said, effects should not be "too much." Default intensity will be 0.3-0.4 (light-moderate). Effects enhance the video, not overpower it.
- **Copyright safety:** Visual effects actually help with copyright differentiation (the safety checker scores visual similarity). Adding effects improves the fair use argument.
