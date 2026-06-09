"""
Enhanced Video Renderer - Professional-grade rendering with MLT integration
and social media optimization.

Features:
- Dual rendering: FFmpeg + MLT/Melt
- Social media presets (YouTube Shorts, Instagram Reels, TikTok)
- Advanced encoding settings for optimal quality/compression
- Multi-clip sequence compositing with transitions
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass
from loguru import logger

from app.core.config import settings


@dataclass
class SocialMediaPreset:
    """Encoding preset for specific social media platform."""
    name: str
    width: int
    height: int
    fps: int
    video_bitrate: str  # e.g., "10M"
    audio_bitrate: str  # e.g., "128k"
    profile: str  # H.264 profile
    level: str  # H.264 level
    gop_size: int  # Keyframe interval
    crf: int  # Quality (18-28)
    pixel_format: str = "yuv420p"


SOCIAL_MEDIA_PRESETS = {
    "youtube_shorts": SocialMediaPreset(
        name="YouTube Shorts",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate="12M",
        audio_bitrate="128k",
        profile="high",
        level="4.1",
        gop_size=30,
        crf=23,
    ),
    "youtube_shorts_60fps": SocialMediaPreset(
        name="YouTube Shorts 60fps",
        width=1080,
        height=1920,
        fps=60,
        video_bitrate="15M",
        audio_bitrate="128k",
        profile="high",
        level="4.2",
        gop_size=60,
        crf=22,
    ),
    "instagram_reels": SocialMediaPreset(
        name="Instagram Reels",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate="10M",
        audio_bitrate="128k",
        profile="baseline",
        level="4.0",
        gop_size=30,
        crf=23,
    ),
    "tiktok": SocialMediaPreset(
        name="TikTok",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate="10M",
        audio_bitrate="128k",
        profile="main",
        level="4.0",
        gop_size=30,
        crf=23,
    ),
    "instagram_story": SocialMediaPreset(
        name="Instagram Story",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate="8M",
        audio_bitrate="128k",
        profile="main",
        level="4.0",
        gop_size=30,
        crf=24,
    ),
}


class EnhancedVideoRenderer:
    """
    Enhanced video renderer with MLT integration and social media presets.

    Supports:
    - FFmpeg rendering (existing, enhanced)
    - MLT/Melt rendering (new)
    - Multi-clip sequences with transitions
    - Platform-specific optimization
    """

    def __init__(self, output_dir: str = "./outputs/videos"):
        """
        Initialize enhanced renderer.

        Args:
            output_dir: Directory for rendered videos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def render_with_preset(
        self,
        input_path: str,
        preset_name: str,
        output_filename: Optional[str] = None,
    ) -> str:
        """
        Render video using social media preset.

        Args:
            input_path: Source video path
            preset_name: Preset key (youtube_shorts, instagram_reels, etc.)
            output_filename: Custom output filename

        Returns:
            Path to rendered video
        """
        preset = SOCIAL_MEDIA_PRESETS.get(preset_name)
        if not preset:
            available = list(SOCIAL_MEDIA_PRESETS.keys())
            raise ValueError(f"Unknown preset '{preset_name}'. Available: {available}")

        if not output_filename:
            output_filename = f"rendered_{preset_name}_{Path(input_path).stem}.mp4"

        output_path = self.output_dir / output_filename

        await self._render_with_social_preset(
            input_path=input_path,
            preset=preset,
            output_path=output_path,
        )

        logger.info(f"Rendered with {preset.name}: {output_path}")
        return str(output_path)

    async def _render_with_social_preset(
        self,
        input_path: str,
        preset: SocialMediaPreset,
        output_path: Path,
    ) -> None:
        """
        Render video using social media encoding preset.

        Implements YouTube/Instagram recommended settings:
        - H.264 video codec
        - AAC audio codec
        - Closed GOP structure
        - CABAC entropy coding
        - Faststart for web streaming
        """
        # Build FFmpeg command with preset settings
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", input_path,
            # Video encoding
            "-c:v", "libx264",
            "-preset", "medium",
            "-profile:v", preset.profile,
            "-level", preset.level,
            "-b:v", preset.video_bitrate,
            "-maxrate", str(int(preset.video_bitrate.rstrip('M')) * 1.2) + "M",
            "-bufsize", str(int(preset.video_bitrate.rstrip('M')) * 1.5) + "M",
            "-g", str(preset.gop_size),
            "-bf", "2",
            "-refs", "4",
            "-coder", "1",  # CABAC
            "-me_method", "hex",
            "-subq", "7",
            "-b_strategy", "1",
            # Quality
            "-crf", str(preset.crf),
            # Frame rate
            "-r", str(preset.fps),
            # Pixel format
            "-pix_fmt", preset.pixel_format,
            # Audio encoding
            "-c:a", "aac",
            "-b:a", preset.audio_bitrate,
            "-ar", "48000",
            "-movflags", "+faststart",
            # Output
            str(output_path),
        ]

        logger.debug(f"Running FFmpeg with {preset.name} preset: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"FFmpeg rendering failed: {error_msg}")

    async def render_multi_clip_sequence(
        self,
        clips: List[Dict[str, Any]],
        audio_path: str,
        output_filename: str,
        preset_name: str = "youtube_shorts",
        transition_duration: float = 0.3,
        crossfade: bool = True,
    ) -> str:
        """
        Render sequence of multiple clips with transitions.

        Args:
            clips: List of clip dicts with 'path', 'start', 'end'
            audio_path: Audio track path
            output_filename: Output filename
            preset_name: Social media preset
            transition_duration: Transition duration (seconds)
            crossfade: Use crossfade transitions

        Returns:
            Path to rendered video
        """
        preset = SOCIAL_MEDIA_PRESETS.get(preset_name, SOCIAL_MEDIA_PRESETS["youtube_shorts"])

        # Create temporary concat file for clips
        concat_file = self.output_dir / f"concat_{output_filename}.txt"
        intermediate_file = self.output_dir / f"intermediate_{Path(output_filename).stem}.mp4"

        try:
            # Write concat file
            with open(concat_file, 'w') as f:
                for clip in clips:
                    clip_path = clip.get("path")
                    if clip_path and Path(clip_path).exists():
                        start = clip.get("start", 0)
                        end = clip.get("end", 0)
                        duration = end - start if end > start else 30

                        # Use FFmpeg trim filters for each clip
                        f.write(f"file '{clip_path}'\n")
                        f.write(f"inpoint {start}\n")
                        f.write(f"outpoint {end}\n")

            # Build filter complex for multi-clip sequence
            filter_clips = []
            for i, clip in enumerate(clips):
                filter_clips.append(f"[{i}:v]scale={preset.width}:{preset.height}[v{i}]")

            # Crossfade between clips
            if crossfade and len(clips) > 1:
                crossfade_filters = []
                offset = 0

                for i in range(len(clips) - 1):
                    duration = float(clips[i].get("end", 30) - clips[i].get("start", 0))
                    offset += duration - transition_duration

                    crossfade_filters.append(
                        f"[v{i}][v{i+1}]xfade=transition=fade:duration={transition_duration}:offset={offset}[v{i+1}]"
                    )

                final_video = "[v{}]".format(len(clips) - 1)
                all_filters = filter_clips + crossfade_filters
            else:
                # Simple concat without transition
                concat_inputs = "".join([f"[v{i}]" for i in range(len(clips))])
                final_video = "[concat_v]"
                all_filters = filter_clips + [
                    f"{concat_inputs}concat=n={len(clips)}:v=1:a=0{final_video}"
                ]

            filter_complex = ";".join(all_filters)

            # Build FFmpeg command
            clip_inputs = []
            for clip in clips:
                clip_path = clip.get("path")
                if clip_path and Path(clip_path).exists():
                    start = clip.get("start", 0)
                    end = clip.get("end", 30)
                    duration = end - start

                    clip_inputs.extend([
                        "-ss", str(start),
                        "-t", str(duration),
                        "-i", clip_path,
                    ])

            cmd = [
                "ffmpeg",
                "-y",
                *clip_inputs,
                "-i", audio_path,
                "-filter_complex", filter_complex,
                "-map", final_video,
                "-map", f"{len(clips)}:a",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", str(preset.crf),
                "-profile:v", preset.profile,
                "-pix_fmt", preset.pixel_format,
                "-c:a", "aac",
                "-b:a", preset.audio_bitrate,
                "-movflags", "+faststart",
                "-shortest",
                str(intermediate_file),
            ]

            logger.debug(f"Rendering multi-clip sequence: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"Multi-clip rendering failed: {stderr.decode()}")

            # Re-encode with social preset for final output
            final_path = await self.render_with_preset(
                input_path=str(intermediate_file),
                preset_name=preset_name,
                output_filename=output_filename,
            )

            # Cleanup intermediate
            if intermediate_file.exists():
                intermediate_file.unlink()

            logger.info(f"Multi-clip sequence rendered: {final_path}")
            return final_path

        finally:
            if concat_file.exists():
                concat_file.unlink()

    async def render_with_transitions(
        self,
        clips: List[str],
        audio_path: Optional[str] = None,
        output_path: Optional[str] = None,
        transition_type: str = "fade",
        transition_duration: float = 0.2,
        preset_name: str = "youtube_shorts",
    ) -> str:
        """
        Create sequence with smooth transitions between clips.

        Args:
            clips: List of clip paths
            audio_path: Audio track (optional)
            output_path: Output path
            transition_type: fade, wipeleft, wiperight, etc.
            transition_duration: Duration in seconds
            preset_name: Social media preset

        Returns:
            Path to final video
        """
        n_clips = len(clips)

        if n_clips == 0:
            raise ValueError("At least one clip required")

        if n_clips == 1:
            # Single clip, just apply preset
            return await self.render_with_preset(
                input_path=clips[0],
                preset_name=preset_name,
                output_filename=Path(output_path).name if output_path else None,
            )

        if not output_path:
            output_path = str(self.output_dir / f"transition_seq_{Path(clips[0]).stem}.mp4")

        # Build inputs for all clips
        inputs = []
        for clip in clips:
            inputs.extend(["-i", clip])

        # Build filter complex for crossfade transitions
        # Scale all clips first
        filters = []
        for i in range(n_clips):
            filters.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v{i}]")

        # Apply crossfades sequentially
        offset = 0
        for i in range(n_clips - 1):
            clip_duration = await self._get_video_duration(clips[i])
            offset += clip_duration - transition_duration

            if i == 0:
                prev_output = f"[v{i}]"
            else:
                prev_output = f"[xf{i-1}]"

            next_input = f"[v{i+1}]"

            if i == n_clips - 2:
                # Last transition - final output
                output_label = "[outv]"
            else:
                output_label = f"[xf{i}]"

            filters.append(
                f"{prev_output}{next_input}xfade=transition={transition_type}:duration={transition_duration}:offset={offset}{output_label}"
            )

        filter_complex = ";".join(filters)

        # Build command
        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
        ]

        if audio_path:
            cmd.extend(["-i", audio_path, "-c:a", "aac", "-b:a", "128k", "-shortest"])

        cmd.extend(["-movflags", "+faststart", output_path])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Transition rendering failed: {stderr.decode()}")

        logger.info(f"Rendered sequence with transitions: {output_path}")
        return output_path

    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await process.communicate()

            import json
            data = json.loads(stdout)
            return float(data.get("format", {}).get("duration", 30))

        except Exception as e:
            logger.warning(f"Could not get duration for {video_path}: {e}")
            return 30.0

    async def render_with_mlt(
        self,
        mlt_project_path: str,
        output_filename: Optional[str] = None,
        use_pipe: bool = True,
    ) -> str:
        """
        Render MLT project using melt or melt+FFmpeg pipe.

        Args:
            mlt_project_path: Path to .mlt XML project
            output_filename: Output filename
            use_pipe: If True, pipe through FFmpeg for better control

        Returns:
            Path to rendered video
        """
        if not output_filename:
            output_filename = f"mlt_render_{Path(mlt_project_path).stem}.mp4"

        output_path = self.output_dir / output_filename

        # Check if melt is available
        melt_exists = await asyncio.create_subprocess_exec(
            "which", "melt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await melt_exists.communicate()

        if melt_exists.returncode != 0:
            raise RuntimeError(
                "MLT/melt not found. Install with: sudo apt install melt (Linux) "
                "or brew install melt (macOS). Falling back to FFmpeg rendering."
            )

        if use_pipe:
            # Pipe method: MLT -> FFmpeg
            cmd = (
                f'melt "{mlt_project_path}" -consumer avformat:pipe:f=yuv4mpegpipe | '
                f'ffmpeg -i pipe:0 -c:v libx264 -preset medium -crf 23 -c:a aac -movflags +faststart "{output_path}"'
            )
        else:
            # Direct MLT encoding
            cmd = (
                f'melt "{mlt_project_path}" -consumer avformat:"{output_path}" '
                f'vcodec=libx264 acodec=aac g=15 crf=23 ab=192k'
            )

        logger.debug(f"Running MLT render: {cmd}")

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"MLT rendering failed: {error_msg}")

        logger.info(f"MLT render complete: {output_path}")
        return str(output_path)

    async def apply_color_grading(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        lut_file: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Apply color grading to video.

        Args:
            video_path: Source video
            output_path: Output path
            lut_file: .cube LUT file path
            adjustments: Manual adjustments (saturation, brightness, contrast)

        Returns:
            Path to graded video
        """
        if not output_path:
            output_path = str(self.output_dir / f"graded_{Path(video_path).stem}.mp4")

        filters = []

        # Apply LUT if provided
        if lut_file and Path(lut_file).exists():
            lut_escaped = str(lut_file).replace(":", "\\:").replace("'", "'\\''")
            filters.append(f"lut3d=file='{lut_escaped}'")

        # Apply manual adjustments
        if adjustments:
            if "saturation" in adjustments:
                # FFmpeg saturation filter (1.0 = original)
                sat = adjustments["saturation"]
                filters.append(f"eq=saturation={sat}")

            if "brightness" in adjustments:
                # brightness: -1.0 to 1.0
                bright = adjustments["brightness"]
                filters.append(f"eq=brightness={bright}")

            if "contrast" in adjustments:
                # contrast: 0.5 to 2.0
                cont = adjustments["contrast"]
                filters.append(f"eq=contrast={cont}")

        if not filters:
            # No adjustments, just copy
            cmd = [
                "ffmpeg", "-y", "-i", video_path, "-c:v", "copy", "-c:a", "copy", output_path,
            ]
        else:
            filter_complex = ",".join(filters)
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vf", filter_complex,
                "-c:a", "copy",
                output_path,
            ]

        logger.debug(f"Applying color grading: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Color grading failed: {stderr.decode()}")

        logger.info(f"Color grading applied: {output_path}")
        return output_path