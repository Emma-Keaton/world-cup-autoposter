# Automated Video Creation Pipeline Documentation

Complete guide to the automated video creation system for FIFA World Cup 2026 content.

## Overview

This system creates short-form football content (30-60 seconds) for YouTube Shorts and Instagram Reels using:
- **Multi-clip sequences** (6-12 clips, 2-5 seconds each)
- **Copyright-safe editing** (heavy edits to avoid Content ID)
- **Double verification** (fair use scoring + quality checks)
- **Competitor monitoring** (auto-watch inspiration channels)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Content Brief (LLM)                       │
│  Topic: "Mbappe's Tactical Evolution at World Cup 2026"     │
│  Script: 30-second narration with hook, build, payoff       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Clip Sequence Planner                              │
│  - Analyzes script structure                                 │
│  - Maps to 6-12 visual moments                               │
│  - Defines narrative roles (hook, build, climax, payoff)     │
│  - Output: SequencePlan JSON                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: TTS + Subtitles                                    │
│  - Edge-TTS commentator voice                                │
│  - Faster-whisper transcription                              │
│  - ASS styled subtitles with animations                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Source Acquisition                                 │
│  - Monitored YouTube channels (FIFA, Tifo, broadcasters)     │
│  - Footballia historical archive                             │
│  - Pexels/Pixabay stock footage                              │
│  - Auto-download relevant uploads                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Advanced Clip Editor                               │
│  - Speed ramp (1.05x - 1.15x faster)                         │
│  - Digital zoom/pan (1.0 - 1.2x)                             │
│  - Color grading (saturation +25%, contrast +15%)            │
│  - Vertical crop (1080x1920)                                 │
│  - Sharpness enhancement                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 5: Sequence Assembly                                  │
│  - Crossfade transitions (0.2-0.3s)                          │
│  - Audio mixing (voiceover + background music)               │
│  - Subtitleoverlay                                           │
│  - Graphics/text overlays                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 6: Final Rendering                                    │
│  - Social media presets (YouTube Shorts, Reels, TikTok)      │
│  - H.264 High Profile @ L4.1                                 │
│  - AAC 128kbps                                               │
│  - Faststart for web streaming                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 7: Double Verification                                │
│  - Copyright Safety Check (4-factor fair use)                │
│  - Audio fingerprint comparison                              │
│  - Visual similarity scoring                                 │
│  - Quality score (min 70/100 to approve)                     │
│  - Auto-fix: enhanced grading if score < 70                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Output: MP4 Ready for Publishing                            │
│  - Video: 1080x1920, 30fps, 12Mbps                          │
│  - Audio: AAC 128kbps, 48kHz                                │
│  - Duration: 30-60 seconds                                   │
│  - Copyright score: 80+/100 (LOW risk)                       │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

```bash
# System dependencies
# Windows (via Chocolatey)
choco install ffmpeg

# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Python Dependencies

Already included in `pyproject.toml`:
```toml
# Video processing
moviepy>=1.0.3
imageio-ffmpeg>=0.4.9

# Audio
edge-tts>=6.1.15
faster-whisper>=1.0.0
librosa>=0.10.0

# Image processing
pillow>=10.2.0
imagehash  # For perceptual hashing
```

Install new dependencies:
```bash
pip install feedparser imagehash
pip install -e .
```

## Monitored Channels

The system automatically monitors these inspiration channels:

### Tactical Analysis (SAFE formats to emulate)
| Channel | Content Type | Copyright Risk | Use Case |
|---------|--------------|----------------|----------|
| Tifo Football | Animated analysis | LOW | Format inspiration |
| Football Made Simple | Simplified tactics | LOW | Visual style |
| Nouman | Tactical breakdowns | LOW | Storytelling |

### Official Sources (NEWS only)
| Channel | Content Type | Copyright Risk | Use Case |
|---------|--------------|----------------|----------|
| FIFA Official | Trailers, announcements | HIGH | News topics only |

### Broadcasters (Fair use clips)
| Channel | Content Type | Copyright Risk | Usage |
|---------|--------------|----------------|--------|
| FOX Soccer | Highlights | HIGH | 3-5s clips with heavy edits |
| Sky Sports Football | Match highlights | HIGH | 3-5s clips with heavy edits |
| ESPN FC | Analysis, news | MEDIUM | Commentary over clips |

### Archive Sources
| Source | Content Type | Copyright Risk | Usage |
|--------|--------------|----------------|--------|
| Footballia | Full historical matches | MEDIUM | Short clips only |

## API Usage

### Create Complete Video (Automated Pipeline)

```bash
POST /api/pipeline/create
```

**Request:**
```json
{
  "brief_id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "youtube_shorts",
  "edit_style": "heavy_editing",
  "skip_verification": false
}
```

**Response:**
```json
{
  "job_id": "abc123-def456",
  "brief_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "estimated_time_seconds": 180,
  "platform": "youtube_shorts"
}
```

### Preview Sequence (Before Rendering)

```bash
POST /api/pipeline/preview/{brief_id}
```

Returns detailed clip plan showing:
- Number of clips planned
- Duration of each clip
- Visual types (action, crowd, tactical, etc.)
- Narrative structure

### Verify Video Copyright

```bash
POST /api/pipeline/verify
```

**Request:**
```json
{
  "video_path": "/path/to/video.mp4",
  "source_paths": ["/path/to/source1.mp4"],
  "script": "Your narration script here..."
}
```

**Response:**
```json
{
  "approved": true,
  "overall_score": 85.5,
  "risk_level": "low",
  "factors": {
    "purpose_character": 90,
    "nature_of_work": 70,
    "amount_used": 80,
    "market_effect": 85
  },
  "checks": [
    {
      "name": "transformative_elements",
      "passed": true,
      "score": 90,
      "details": "Substantial narration (75 words)"
    },
    {
      "name": "audio_fingerprint",
      "passed": true,
      "score": 85,
      "details": "Audio significantly modified"
    }
  ],
  "recommendations": []
}
```

### Monitor Competitors

```bash
# List monitored channels
GET /api/pipeline/monitor/channels

# Check for new uploads
POST /api/pipeline/monitor/check

# Add custom channel
POST /api/pipeline/monitor/channels
{
  "name": "My Favorite Analyst",
  "youtube_url": "https://youtube.com/@channel",
  "content_type": "analysis"
}

# List monitored uploads
GET /api/pipeline/monitor/uploads?limit=50&downloaded_only=false

# Download specific upload
POST /api/pipeline/monitor/download
{
  "upload_id": "youtube_video_id"
}
```

### Batch Processing

```bash
POST /api/pipeline/batch
{
  "brief_ids": ["id1", "id2", "id3"],
  "platform": "instagram_reels",
  "max_concurrent": 3
}
```

## Programmatic Usage

### Full Pipeline

```python
from app.renderer.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig

# Configure pipeline
config = PipelineConfig(
    platform="youtube_shorts",
    edit_style="heavy_editing",
    require_verification=True,
    min_copyright_score=70,
)

# Initialize
orchestrator = PipelineOrchestrator(config=config)

# Create video from brief
result = await orchestrator.create_video_from_brief(
    brief=content_brief,
    source_materials=["/path/to/sources"],  # Optional
)

# Check result
if result.success:
    print(f"Video: {result.video_path}")
    print(f"Copyright score: {result.copyright_report.overall_score}")
    print(f"Risk level: {result.copyright_report.risk_level.value}")
else:
    print(f"Errors: {result.errors}")
```

### Clip Sequence Planning

```python
from app.renderer.clip_sequence_planner import ClipSequencePlanner

planner = ClipSequencePlanner(max_clip_duration=5.0)

plan = await planner.plan_from_script(
    script="Mbappe has revolutionized the false 9 role...",
    audio_duration=30.0,
    topic="Mbappe tactical analysis",
)

print(f"Planned {plan.clip_count} clips")
print(f"Visual rhythm: {plan.visual_rhythm}")

# Export to JSON
await planner.export_plan(plan, "sequence_plan.json")
```

### Advanced Editing

```python
from app.renderer.advanced_clip_editor import AdvancedClipEditor

editor = AdvancedClipEditor()

# Create edited sequence
edited = await editor.create_edited_sequence(
    source_clips=[{"path": "clip1.mp4"}, {"path": "clip2.mp4"}],
    sequence_plan=plan,
    audio_path="voiceover.mp3",
    edit_style="heavy_editing",  # Applies all copyright-safe edits
)

# Apply additional effects
with_graphics = await editor.apply_motion_graphics(
    video_path=edited,
    graphics_type="stats_overlay",
)
```

### Enhanced Rendering

```python
from app.renderer.video_renderer_enhanced import EnhancedVideoRenderer

renderer = EnhancedVideoRenderer()

# Render with social media preset
final = await renderer.render_with_preset(
    input_path=edited,
    preset_name="youtube_shorts",  # or instagram_reels, tiktok
)

# Multi-clip sequence with transitions
final = await renderer.render_with_transitions(
    clips=["clip1.mp4", "clip2.mp4", "clip3.mp4"],
    audio_path="audio.mp3",
    transition_type="fade",
    transition_duration=0.3,
)
```

### Copyright Checking

```python
from app.core.copyright_checker import CopyrightSafetyChecker

checker = CopyrightSafetyChecker()

report = await checker.verify_fair_use(
    video_path="final.mp4",
    source_materials=["source1.mp4", "source2.mp4"],
    script="Your narration here",
    editing_metadata={
        "clip_count": 8,
        "avg_clip_duration": 3.5,
        "effects_applied": ["speed_ramp", "zoom", "color_grade"],
    },
)

print(f"Score: {report.overall_score}/100")
print(f"Risk: {report.risk_level.value}")
print(f"Approved: {report.approved}")

if not report.approved:
    print("Recommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")
```

## Copyright Safety

### Four-Factor Fair Use Analysis

The system evaluates:

1. **Purpose & Character (35% weight)**
   - Transformative commentary
   - Educational/analytical nature
   - Added value through editing

2. **Nature of Work (15% weight)**
   - Factual vs. creative content
   - Sports broadcasts are factual (favors fair use)

3. **Amount Used (25% weight)**
   - Short clips (2-5 seconds each)
   - Multiple sources (6+ clips)
   - Total duration under 60 seconds

4. **Market Effect (25% weight)**
   - Doesn't substitute for original
   - Commentary adds new value
   - Short-form is promotional

### Risk Levels

| Score | Risk Level | Action |
|-------|------------|--------|
| 80-100 | LOW | Auto-approve |
| 60-79 | MEDIUM | Review recommended |
| 40-59 | HIGH | Requires edits |
| 0-39 | CRITICAL | Reject, re-edit |

### Auto-Fix Techniques

If score < 70, system automatically applies:

```python
# Enhanced color grading
adjustments = {
    "saturation": 1.3,      # +30%
    "contrast": 1.2,        # +20%
    "brightness": 0.1,      # +10%
}

# Additional audio modification
cmd = "ffmpeg -i audio.mp3 -af asetrate=44100*1.122,atempo=0.89 audio_modified.mp3"

# Re-verify after fixes
```

## Encoding Specifications

### YouTube Shorts

```
Container: MP4
Video: H.264 High Profile @ Level 4.1
Resolution: 1080x1920 (9:16 vertical)
Frame rate: 30 or 60 fps
Bitrate: 12 Mbps VBR (max 15 Mbps)
Audio: AAC-LC 128kbps, 48kHz
GOP: 30 frames (closed)
Faststart: Enabled
```

### Instagram Reels

```
Container: MP4
Video: H.264 Baseline Profile @ Level 4.0
Resolution: 1080x1920 (9:16 vertical)
Frame rate: 30 fps
Bitrate: 10 Mbps VBR
Audio: AAC-LC 128kbps, 48kHz
Faststart: Enabled
```

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Install FFmpeg
choco install ffmpeg  # Windows
sudo apt install ffmpeg  # Linux
brew install ffmpeg  # macOS
```

**Audio fingerprinting unavailable:**
```bash
pip install librosa
```

**Visual hashing unavailable:**
```bash
pip install pillow imagehash
```

**RSS monitoring not working:**
```bash
pip install feedparser
```

### Debug Pipeline

```python
# Enable debug logging
LOG_LEVEL=DEBUG

# Preview sequence before rendering
preview = await orchestrator.preview_sequence(brief)
print(json.dumps(preview, indent=2))

# Run verification only
report = await checker.verify_fair_use(...)
```

## Best Practices

### Content Strategy

1. **Use inspiration channels for format, not footage**
   - Tifo-style animations → Create your own graphics
   - COPA90 storytelling → Emulate narrative structure

2. **Keep clips short and varied**
   - 2-5 seconds per clip
   - 6+ different sources
   - Mix of action, reactions, crowds

3. **Heavy editing is essential**
   - Speed ramp all footage
   - Apply color grading
   - Add zoom/pan movement
   - Layer graphics/text

4. **Strong narration makes it transformative**
   - 50+ words of commentary
   - Analytical language (why, how, because)
   - Clear point of view

### Avoiding Content ID

**DO:**
- ✅ 3-5 second clips max
- ✅ Speed up 5-15%
- ✅ Pitch shift audio
- ✅ Heavy color grading
- ✅ Add commentary throughout
- ✅ Use multiple sources
- ✅ Add graphics and text

**DON'T:**
- ❌ Clip longer than 10 seconds
- ❌ Use original audio without modification
- ❌ Upload continuous sequences
- ❌ Use iconic moments without transformation
- ❌ Minimal editing

## File Structure

```
app/
├── renderer/
│   ├── video_renderer_enhanced.py    # Enhanced rendering with presets
│   ├── advanced_clip_editor.py       # Multi-clip editing, copyright-safe
│   ├── clip_sequence_planner.py      # Script-to-visual mapping
│   ├── pipeline_orchestrator.py      # End-to-end automation
│   ├── tts_engine.py                 # Edge-TTS voiceover
│   └── subtitle_generator.py         # Faster-whisper subtitles
├── core/
│   ├── copyright_checker.py          # Fair use scoring
│   └── competitor_monitor.py         # Channel monitoring
└── api/
    └── pipeline.py                   # Pipeline API endpoints
```

## Next Steps

1. **Configure monitored channels** for your niche
2. **Test pipeline** with a sample brief
3. **Adjust edit style** based on copyright scores
4. **Enable batch processing** for scale
5. **Set up auto-publishing** to platforms