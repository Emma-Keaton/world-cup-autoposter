"""
Video renderer using MoviePy and FFmpeg.
Stitches together assets, audio, and subtitles into final video.
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from app.core.config import settings


class VideoRenderer:
    """
    Renders final videos using MoviePy and FFmpeg.
    
    Combines:
    - Background video clips/images
    - TTS audio track
    - Background music
    - Dynamic subtitles
    - Overlay effects
    """
    
    def __init__(self, output_dir: str = "./outputs/videos"):
        """
        Initialize video renderer.
        
        Args:
            output_dir: Directory for rendered videos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Video specs from settings
        self.width = settings.VIDEO_WIDTH
        self.height = settings.VIDEO_HEIGHT
        self.fps = settings.VIDEO_FPS
        self.target_duration = settings.VIDEO_DURATION_SECONDS
    
    async def render_video(
        self,
        audio_path: str,
        subtitle_path: Optional[str] = None,
        background_assets: Optional[List[str]] = None,
        music_path: Optional[str] = None,
        output_filename: Optional[str] = None,
        visual_style: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Render complete video.
        
        Args:
            audio_path: Path to TTS audio file
            subtitle_path: Path to subtitle file (ASS/SRT)
            background_assets: List of video/image paths
            music_path: Path to background music
            output_filename: Custom output filename
            visual_style: Visual direction from content brief
            
        Returns:
            Path to rendered video
        """
        import uuid
        
        if not output_filename:
            output_filename = f"{uuid.uuid4()}.mp4"
        
        output_path = self.output_dir / output_filename
        
        # Get audio duration for video length
        audio_duration = await self._get_media_duration(audio_path)
        
        try:
            # Use FFmpeg for rendering (more reliable than MoviePy for complex compositions)
            await self._render_with_ffmpeg(
                audio_path=audio_path,
                subtitle_path=subtitle_path,
                background_assets=background_assets,
                music_path=music_path,
                output_path=output_path,
                duration=audio_duration,
                visual_style=visual_style or {},
            )
            
            logger.info(f"Rendered video: {output_path} ({audio_duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Video rendering failed: {e}")
            raise
    
    async def _render_with_ffmpeg(
        self,
        audio_path: str,
        subtitle_path: Optional[str],
        background_assets: Optional[List[str]],
        music_path: Optional[str],
        output_path: Path,
        duration: float,
        visual_style: Dict[str, str],
    ) -> None:
        """
        Render video using FFmpeg.
        
        Args:
            audio_path: TTS audio
            subtitle_path: Subtitle file
            background_assets: Background visuals
            music_path: Background music
            output_path: Output path
            duration: Target duration
            visual_style: Style preferences
        """
        # Build FFmpeg filter complex for compositing
        
        # Start with background (color or first asset)
        if background_assets and Path(background_assets[0]).exists():
            # Use actual video asset
            video_input = ["-i", background_assets[0]]
            
            # Loop short clips to fill duration
            video_filter = f"[0:v]loop=loop=-1:size=2:start=0,trim=duration={duration}[bg]"
        else:
            # Solid color background (gradient for football theme)
            video_input = []
            video_filter = f"color=c=0x1a4d2e:s={self.width}x{self.height}:d={duration}[bg]"
        
        inputs = video_input.copy()
        filters = [video_filter]
        
        # Add audio
        inputs.extend(["-i", audio_path])
        audio_idx = len(inputs) - 1
        filters.append(f"[{audio_idx}:a]anull[audio]")
        
        # Add background music if provided
        if music_path and Path(music_path).exists():
            inputs.extend(["-i", music_path])
            music_idx = len(inputs) - 1
            
            # Mix music with voice (duck music by -15dB)
            filters.append(f"[{music_idx}:a]volume=0.3[music]")
            filters.append(f"[audio][music]amix=inputs=2:duration=first:dropout_transition=3[final_audio]")
            audio_output = "final_audio"
        else:
            audio_output = "audio"
        
        # Add subtitles if provided
        if subtitle_path and Path(subtitle_path).exists():
            # Escape subtitle path for FFmpeg
            subtitle_escaped = str(subtitle_path).replace("'", "'\\''").replace(":", "\\:")
            
            # Determine subtitle format
            sub_ext = subtitle_path.suffix.lower()
            if sub_ext == ".ass":
                filters.append(f"[bg]ass='{subtitle_escaped}'[video]")
            elif sub_ext == ".srt":
                filters.append(f"[bg]subtitles='{subtitle_escaped}'[video]")
            else:
                filters.append(f"[bg]null[video]")
            
            video_output = "video"
        else:
            video_output = "bg"
        
        # Build final filter graph
        filter_complex = ";".join(filters)
        
        # FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
        ]
        
        # Add inputs
        for i in range(0, len(inputs), 2):
            cmd.extend([inputs[i], inputs[i + 1]])
        
        # Add filter
        cmd.extend(["-filter_complex", filter_complex])
        
        # Map outputs
        cmd.extend(["-map", f"[{video_output}]"])
        cmd.extend(["-map", f"[{audio_output}]"])
        
        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path),
        ])
        
        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
        
        # Execute
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {stderr.decode() if stderr else 'Unknown error'}")
    
    async def _get_media_duration(self, media_path: str) -> float:
        """Get duration of media file using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                media_path,
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
            logger.warning(f"Could not get media duration: {e}, using default 30s")
            return 30.0
    
    async def create_thumbnail(
        self,
        video_path: str,
        output_path: str,
        text_overlay: Optional[str] = None,
        style: Dict[str, str] = None,
    ) -> str:
        """
        Generate thumbnail from video.
        
        Args:
            video_path: Source video
            output_path: Thumbnail output path
            text_overlay: Optional text to overlay
            style: Style options
            
        Returns:
            Path to thumbnail
        """
        # Extract frame from middle of video
        duration = await self._get_media_duration(video_path)
        seek_time = duration / 2
        
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(seek_time),
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"scale={self.width}:{self.height}",
            output_path,
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Thumbnail extraction failed: {stderr.decode()}")
            return ""
        
        logger.info(f"Created thumbnail: {output_path}")
        return output_path
    
    async def create_compilation(
        self,
        clips: List[Dict[str, Any]],
        audio_path: str,
        output_filename: str,
    ) -> str:
        """
        Create video compilation from multiple clips.
        
        Args:
            clips: List of clip metadata with paths and durations
            audio_path: Audio track path
            output_filename: Output filename
            
        Returns:
            Path to compilation video
        """
        # Concatenate clips using FFmpeg concat demuxer
        concat_file = self.output_dir / "concat_list.txt"
        
        with open(concat_file, 'w') as f:
            for clip in clips:
                clip_path = clip.get("path")
                if clip_path and Path(clip_path).exists():
                    f.write(f"file '{clip_path}'\n")
        
        output_path = self.output_dir / output_filename
        
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            str(output_path),
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Compilation failed: {stderr.decode()}")
        
        # Cleanup
        concat_file.unlink(missing_ok=True)
        
        return str(output_path)