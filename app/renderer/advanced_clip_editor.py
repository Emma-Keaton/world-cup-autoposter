"""Advanced Clip Editor - Multi-clip editing with copyright-safe techniques.

Features:
- Multi-layer composition (base + overlays + graphics)
- Copyright avoidance editing (zoom, crop, color grade, speed ramp)
- Dynamic transitions between clips
- Motion graphics and effects
- Heavy editing to prevent Content ID detection
- Visual effects engine (shot, motion, celebration, emotion, scream, overlays, style presets)
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from app.renderer.clip_sequence_planner import ClipPlan, SequencePlan
from app.effects.base import EffectContext, EffectResult
from app.effects.registry import get_registry
from app.effects.emotion_visuals import infer_emotion, EMOTION_EFFECT_MAP


@dataclass
class EditSettings:
    """Settings for copyright-safe editing."""

    # Speed/pitch modification
    speed_ramp: Tuple[float, float] = (1.05, 1.15)  # 5-15% faster
    pitch_shift: int = 2  # Semitones

    # Visual modifications
    zoom_range: Tuple[float, float] = (1.0, 1.2)  # 0-20% zoom
    color_variation: Dict[str, float] = None

    # Clip duration limits
    max_clip_duration: float = 5.0
    min_clip_duration: float = 2.0

    # Transitions
    transition_duration: float = 0.3

    def __post_init__(self):
        if self.color_variation is None:
            self.color_variation = {
                "saturation": 1.2,
                "brightness": 1.0,
                "contrast": 1.1,
            }


class AdvancedClipEditor:
    """
    Advanced video editor for copyright-safe multi-clip sequences.

    Applies heavy editing techniques to avoid Content ID detection:
    - Multi-layer compositing
    - Speed/pitch manipulation
    - Color grading
    - Digital zoom/pan
    - Heavy cuts and transitions
    """

    def __init__(self, output_dir: str = "./outputs/edited"):
        """Initialize advanced editor.

        Args:
            output_dir: Directory for edited outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.settings = EditSettings()

    async def create_edited_sequence(
        self,
        source_clips: List[Dict[str, Any]],
        sequence_plan: SequencePlan,
        audio_path: Optional[str] = None,
        output_filename: Optional[str] = None,
        edit_style: str = "heavy_editing",
    ) -> str:
        """Create edited sequence from source clips following plan.

        Args:
            source_clips: Available source clips with paths and metadata
            sequence_plan: Clip sequence plan
            audio_path: Audio track path
            output_filename: Output filename
            edit_style: "heavy_editing", "moderate", "light"

        Returns:
            Path to edited sequence
        """
        if not output_filename:
            output_filename = f"edited_sequence_{Path(source_clips[0]['path']).stem}.mp4"
        output_path = self.output_dir / output_filename

        # Apply edit style settings
        if edit_style == "light":
            self.settings = EditSettings(
                speed_ramp=(1.0, 1.05),
                zoom_range=(1.0, 1.05),
                max_clip_duration=8.0,
            )
        elif edit_style == "moderate":
            self.settings = EditSettings(
                speed_ramp=(1.05, 1.10),
                zoom_range=(1.0, 1.1),
                max_clip_duration=6.0,
            )
        else:  # heavy_editing
            self.settings = EditSettings(
                speed_ramp=(1.05, 1.15),
                zoom_range=(1.0, 1.2),
                max_clip_duration=5.0,
                transition_duration=0.2,
            )

        # Step 1: Process each source clip with copyright-safe edits + effects
        processed_clips = []
        for i, clip_plan in enumerate(sequence_plan.clips):
            # Find matching source
            source = self._find_source_for_clip(clip_plan, source_clips)
            if not source:
                logger.warning(f"No source found for clip {i}")
                continue

            # Process with heavy editing + visual effects
            processed = await self._process_individual_clip(
                source_path=source.get("path"),
                clip_plan=clip_plan,
                output_name=f"processed_{i:03d}.mp4",
            )
            processed_clips.append(processed)

        if not processed_clips:
            raise ValueError("No clips were successfully processed")

        # Step 2: Concatenate with transitions
        final_path = await self._concatenate_with_transitions(
            clips=processed_clips,
            audio_path=audio_path,
            output_path=output_path,
        )

        # Step 3: Apply post-concatenation effects (celebration overlays, data overlays)
        final_path = await self._apply_post_concat_effects(
            video_path=final_path,
            sequence_plan=sequence_plan,
            audio_path=audio_path,
        )

        logger.info(f"Edited sequence created: {final_path}")
        return final_path

    def _find_source_for_clip(
        self,
        clip_plan: ClipPlan,
        source_clips: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Find best matching source clip for planned clip."""
        for source in source_clips:
            if source.get("visual_type") == clip_plan.visual_type.value:
                return source
        return source_clips[0] if source_clips else None

    async def _process_individual_clip(
        self,
        source_path: str,
        clip_plan: ClipPlan,
        output_name: str,
    ) -> Dict[str, Any]:
        """Process individual clip with copyright-safe edits + visual effects engine.

        Applies:
        - Speed ramp
        - Digital zoom/pan
        - Color grading
        - Cropping to vertical
        - Visual effects from the effects engine (shot, motion, emotion, style presets)
        """
        output_path = self.output_dir / output_name

        # Build EffectContext from clip_plan
        intensity = self._edit_style_to_intensity()
        ctx = EffectContext(
            clip_path=source_path,
            duration=clip_plan.duration,
            fps=30,
            width=1080,
            height=1920,
            intensity=intensity,
            narrative_role=clip_plan.narrative_role.value
            if hasattr(clip_plan.narrative_role, "value")
            else str(clip_plan.narrative_role),
            visual_type=clip_plan.visual_type.value
            if hasattr(clip_plan.visual_type, "value")
            else str(clip_plan.visual_type),
            effect_tags=clip_plan.effects,
            text_overlay=clip_plan.text_overlay,
        )

        # Build base FFmpeg filter chain (copyright-safe edits)
        filters = []

        # 1. Speed adjustment
        speed = 1.0 + (self.settings.speed_ramp[1] - self.settings.speed_ramp[0]) * 0.5
        filters.append(f"setpts={1/speed:.3f}*PTS")

        # 2. Scale to vertical (1080x1920)
        filters.append("scale=1080:1920:force_original_aspect_ratio=decrease")
        filters.append("pad=1080:1920:(ow-iw)/2:(oh-ih)/2")

        # 3. Digital zoom (crop + scale)
        zoom_factor = 1.0 + (self.settings.zoom_range[1] - self.settings.zoom_range[0]) * 0.3
        if zoom_factor > 1.0:
            scaled_width = int(1080 * zoom_factor)
            scaled_height = int(1920 * zoom_factor)
            filters.append(f"scale={scaled_width}:{scaled_height}")
            filters.append("crop=1080:1920")

        # 4. Color grading for copyright avoidance
        saturation = self.settings.color_variation.get("saturation", 1.2)
        brightness = self.settings.color_variation.get("brightness", 1.0)
        contrast = self.settings.color_variation.get("contrast", 1.1)
        filters.append(
            f"eq=saturation={saturation}:brightness={brightness-1}:contrast={contrast}"
        )

        # 5. Sharpness
        filters.append("unsharp=5:5:1.0:5:5:0.0")

        # --- Visual Effects Engine ---
        # 6. Apply effects from the effects registry (tag-matched PER_CLIP effects)
        effect_names = []
        try:
            registry = get_registry()
            effect_results = registry.build_effects_for_clip(ctx)

            # Also apply emotion-driven effects (context-based, not tag-based)
            emotion = infer_emotion(ctx)
            for effect_cls in EMOTION_EFFECT_MAP.get(emotion, []):
                effect_instance = effect_cls()
                already_applied = any(
                    r.metadata.get("name") == effect_instance.name
                    for r in effect_results
                    if r.metadata
                )
                if not already_applied:
                    emotion_result = effect_instance.build(ctx)
                    emotion_result.metadata["name"] = effect_instance.name
                    effect_results.append(emotion_result)
                    effect_names.append(effect_instance.name)

            # Merge effect filters into the main chain
            pre_filters = []
            main_filters = []
            for result in effect_results:
                pre_filters.extend(result.pre_filters)
                main_filters.extend(result.filters)
                effect_names.append(result.metadata.get("name", "unknown"))

            # Pre-filters go before base filters, effect filters go after
            filters = pre_filters + filters + main_filters
        except Exception as e:
            logger.warning(f"Effects engine error (falling back to base edits): {e}")

        filter_complex = ",".join(filters)

        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-vf", filter_complex,
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            str(output_path),
        ]

        logger.debug(f"Processing clip: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Clip processing failed: {error_msg}")

        return {
            "path": str(output_path),
            "duration": clip_plan.duration,
            "original_duration": clip_plan.duration * speed,
            "speed_factor": speed,
            "effects_applied": ["speed_ramp", "zoom", "color_grade", "vertical_crop"] + effect_names,
        }

    def _edit_style_to_intensity(self) -> float:
        """Map current edit_style to effects intensity (0.0-1.0)."""
        ramp = self.settings.speed_ramp[1]
        if ramp <= 1.05:
            return 0.3   # light
        elif ramp <= 1.10:
            return 0.5   # moderate
        else:
            return 0.8   # heavy_editing

    async def _apply_post_concat_effects(
        self,
        video_path: str,
        sequence_plan: SequencePlan,
        audio_path: Optional[str] = None,
    ) -> str:
        """Apply POST_CONCAT stage effects (celebration overlays, score bugs, etc.)."""
        intensity = self._edit_style_to_intensity()
        ctx = EffectContext(
            clip_path=video_path,
            duration=sequence_plan.total_duration,
            fps=30,
            width=1080,
            height=1920,
            intensity=intensity,
            narrative_role="climax",
            visual_type="action",
            effect_tags=[tag for clip in sequence_plan.clips for tag in clip.effects],
            audio_path=audio_path,
            extra_data=sequence_plan.clips[0].extra_data if hasattr(sequence_plan.clips[0], 'extra_data') else {},
        )

        try:
            registry = get_registry()
            post_results = registry.build_post_concat_effects(ctx)

            if not post_results:
                return video_path

            # Collect filter-based effects
            all_filters = []
            overlay_dirs = []

            for result in post_results:
                all_filters.extend(result.filters)
                if result.overlay_frames_dir:
                    overlay_dirs.append((result.overlay_frames_dir, result.overlay_blend))

            if not all_filters and not overlay_dirs:
                return video_path

            output_path = str(self.output_dir / f"post_effects_{Path(video_path).stem}.mp4")

            if all_filters:
                filter_complex = ",".join(all_filters)
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-vf", filter_complex,
                    "-c:a", "copy",
                    output_path,
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.warning(f"Post-concat filter effects failed: {stderr.decode()}")
                    return video_path
                video_path = output_path

            # Apply overlay frame sequences (confetti, fireworks, flares)
            for frames_dir, blend_mode in overlay_dirs:
                overlay_output = str(self.output_dir / f"overlay_{Path(video_path).stem}.mp4")
                # Use FFmpeg image2 demuxer to composite PNG sequence over video
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-framerate", str(ctx.fps),
                    "-i", f"{frames_dir}/frame_%04d.png",
                    "-filter_complex",
                    f"[0:v][1:v]overlay=0:0:format={blend_mode}",
                    "-c:a", "copy",
                    overlay_output,
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.warning(f"Overlay compositing failed: {stderr.decode()}")
                    continue
                video_path = overlay_output

        except Exception as e:
            logger.warning(f"Post-concat effects error: {e}")

        return video_path

    async def _concatenate_with_transitions(
        self,
        clips: List[Dict[str, Any]],
        audio_path: Optional[str],
        output_path: Path,
    ) -> str:
        """Concatenate processed clips with smooth transitions."""
        if len(clips) == 1:
            cmd = [
                "ffmpeg", "-y", "-i", clips[0]["path"],
                "-c:v", "copy", "-c:a", "copy",
                str(output_path),
            ]
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.communicate()
            return str(output_path)

        # Multiple clips - create concat file
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip['path']}'\n")

        # Build filter for crossfade transitions
        n_clips = len(clips)
        filter_parts = []

        clip_inputs = []
        for clip in clips:
            clip_inputs.extend(["-i", clip["path"]])

        # Crossfade between consecutive clips
        if n_clips > 1:
            offset = 0
            for i in range(n_clips - 1):
                clip_duration = clips[i]["duration"]
                if i == 0:
                    input1 = "[0:v]"
                else:
                    input1 = f"[xf{i-1}]"

                input2 = f"[{i+1}:v]"
                if i == n_clips - 2:
                    output = "[outv]"
                else:
                    output = f"[xf{i}]"

                offset_sec = offset
                filter_parts.append(
                    f"{input1}{input2}xfade=transition=fade:"
                    f"duration={self.settings.transition_duration}:"
                    f"offset={offset_sec}{output}"
                )
                offset += clip_duration - self.settings.transition_duration

            filter_complex = ";".join(filter_parts)

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-c:v", "libx264", "-preset", "medium",
                "-crf", "23", "-pix_fmt", "yuv420p",
            ]

            if audio_path and Path(audio_path).exists():
                cmd.extend(["-i", audio_path, "-c:a", "aac", "-b:a", "128k", "-shortest"])
            else:
                cmd.extend(["-c:a", "aac", "-b:a", "128k"])

            cmd.extend(["-movflags", "+faststart", str(output_path)])

            logger.debug(f"Concatenating with transitions: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"Transition concatenation failed: {stderr.decode()}")

        # Cleanup
        if concat_file.exists():
            concat_file.unlink()

        return str(output_path)

    async def apply_motion_graphics(
        self,
        video_path: str,
        graphics_type: str = "stats_overlay",
        output_path: Optional[str] = None,
    ) -> str:
        """Apply motion graphics overlay."""
        if not output_path:
            output_path = str(self.output_dir / f"graphics_{Path(video_path).stem}.mp4")

        if graphics_type == "stats_overlay":
            drawbox = "drawbox=x=50:y=1400:w=980:h=200:color=black@0.7:t=fill"
            drawtext = "drawtext=fontsize=24:fontcolor=white:x=70:y=1420:text='STATS_BOX'"
            filter_complex = f"{drawbox},{drawtext}"
        elif graphics_type == "player_name":
            drawbox = "drawbox=x=50:y=1600:w=980:h=150:color=black@0.8:t=fill"
            drawtext = "drawtext=fontsize=32:fontcolor=yellow:x=70:y=1640:text='PLAYER_NAME'"
            filter_complex = f"{drawbox},{drawtext}"
        elif graphics_type == "score_bug":
            drawbox = "drawbox=x=50:y=50:w=400:h=100:color=white@0.9:t=fill"
            drawtext = "drawtext=fontsize=28:fontcolor=black:x=70:y=70:text='SCORE'"
            filter_complex = f"{drawbox},{drawtext}"
        else:
            return video_path

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", filter_complex, "-c:a", "copy",
            output_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Motion graphics failed: {stderr.decode()}")

        logger.info(f"Motion graphics applied: {output_path}")
        return output_path

    async def add_zoom_effects(
        self,
        video_path: str,
        zoom_points: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> str:
        """Add dynamic zoom effects at specific points."""
        if not output_path:
            output_path = str(self.output_dir / f"zoom_{Path(video_path).stem}.mp4")

        zoom_factor = 1.15
        filter_complex = (
            f"zoompan=z='min(zoom+{zoom_factor/100:.3f}, {zoom_factor:.3f})'"
            f":d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        )

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", filter_complex, "-c:a", "copy",
            output_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Zoom effect failed: {stderr.decode()}")
        return output_path

    async def add_text_overlay(
        self,
        video_path: str,
        text: str,
        position: str = "bottom",
        style: str = "bold",
        output_path: Optional[str] = None,
    ) -> str:
        """Add text overlay to video."""
        if not output_path:
            output_path = str(self.output_dir / f"text_{Path(video_path).stem}.mp4")

        positions = {
            "top": "y=50",
            "center": "y=(h-text_h)/2",
            "bottom": "y=h-text_h-50",
        }
        y_pos = positions.get(position, positions["bottom"])

        style_map = {
            "bold": ("yellow", "36", "black"),
            "minimal": ("white", "28", "black"),
            "dramatic": ("yellow", "48", "black"),
        }
        fontcolor, fontsize, border = style_map.get(style, ("white", "32", "black"))

        escaped_text = text.replace("'", "'\\''").replace(":", "\\:")
        filter_complex = (
            f"drawtext=text='{escaped_text}':fontsize={fontsize}:fontcolor={fontcolor}:"
            f"{y_pos}:x=(w-text_w)/2:borderw=2:bordercolor={border}"
        )

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", filter_complex, "-c:a", "copy",
            output_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Text overlay failed: {stderr.decode()}")

        logger.info(f"Text overlay added: {output_path}")
        return output_path
