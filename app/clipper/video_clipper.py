"""
Video Clipper - Extract and process video clips.
Uses FFmpeg for precise cutting and processing.
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger


class VideoClipper:
    """
    Extract and process video clips using FFmpeg.
    
    Features:
    - Precise cutting with keyframe accuracy
    - Resize to 9:16 (vertical) for Reels/Shorts
    - Add subtitles overlay
    - Add branding/watermark
    - Concatenate multiple clips
    """
    
    def __init__(self, output_dir: str = "./outputs/clips"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_filename: Optional[str] = None,
        fast_cut: bool = True,
    ) -> str:
        """
        Extract a clip from a video.
        
        Args:
            video_path: Source video path
            start_time: Start time in seconds
            end_time: End time in seconds
            output_filename: Custom output filename
            fast_cut: Use fast seeking (less accurate but faster)
            
        Returns:
            Path to extracted clip
        """
        if not output_filename:
            import uuid
            output_filename = f"{uuid.uuid4()}.mp4"
        
        output_path = self.output_dir / output_filename
        duration = end_time - start_time
        
        # FFmpeg command
        if fast_cut:
            # Fast method: seek with -ss before -i (may not be frame-accurate)
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "copy",
                "-c:a", "copy",
                "-avoid_negative_ts", "1",
                str(output_path),
            ]
        else:
            # Accurate method: seek with -ss after -i (slower but frame-accurate)
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-ss", str(start_time),
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-avoid_negative_ts", "1",
                str(output_path),
            ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode() if stderr else 'Unknown error'}")
            
            logger.info(f"Extracted clip: {output_path} ({duration:.1f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Clip extraction failed: {e}")
            raise
    
    async def convert_to_vertical(
        self,
        video_path: str,
        output_filename: Optional[str] = None,
        zoom: bool = True,
    ) -> str:
        """
        Convert horizontal video to 9:16 vertical format.
        
        Args:
            video_path: Source video (16:9)
            output_filename: Custom output filename
            zoom: If True, zoom to fill vertical (crop sides). 
                  If False, add pillarboxes (blur background)
            
        Returns:
            Path to vertical video
        """
        if not output_filename:
            import uuid
            output_filename = f"{uuid.uuid4()}_vertical.mp4"
        
        output_path = self.output_dir / output_filename
        
        if zoom:
            # Zoom and crop method (fills vertical frame)
            # Scales video so height fills frame, then crops to 9:16
            filter_complex = (
                "scale=iH*(9/16):ih,"
                "crop=iw:ih"
            )
        else:
            # Pillarbox with blur background method
            filter_complex = (
                "[0:v]scale=trunc(ih*(16/9)/2)*2:ih[main];"
                "[0:v]scale=iw*(9/16):ih*(9/16),boxblur=20:1[bg];"
                "[bg][main]overlay=(W-w)/2:(H-h)/2"
            )
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", filter_complex,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path),
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            logger.info(f"Converted to vertical: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Vertical conversion failed: {e}")
            raise
    
    async def add_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_filename: Optional[str] = None,
        style: str = "dynamic",
    ) -> str:
        """
        Burn subtitles into video.
        
        Args:
            video_path: Source video
            subtitle_path: Subtitle file (SRT or ASS)
            output_filename: Custom output filename
            style: Subtitle style (for auto-conversion)
            
        Returns:
            Path to video with burned-in subtitles
        """
        if not output_filename:
            import uuid
            output_filename = f"{uuid.uuid4}_subtitled.mp4"
        
        output_path = self.output_dir / output_filename
        
        # Escape path for FFmpeg
        subtitle_escaped = str(subtitle_path).replace(":", "\\:").replace("'", "'\\''")
        
        # Determine filter based on subtitle format
        sub_ext = Path(subtitle_path).suffix.lower()
        if sub_ext == ".ass":
            filter_str = f"ass='{subtitle_escaped}'"
        elif sub_ext == ".srt":
            filter_str = f"subtitles='{subtitle_escaped}'"
        elif sub_ext == ".vtt":
            # Convert VTT to SRT first or use subfilter
            filter_str = f"subtitles='{subtitle_escaped}'"
        else:
            filter_str = f"subtitles='{subtitle_escaped}'"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", filter_str,
            "-c:a", "aac",
            str(output_path),
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            logger.info(f"Added subtitles: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Subtitle overlay failed: {e}")
            raise
    
    async def add_watermark(
        self,
        video_path: str,
        watermark_path: str,
        output_filename: Optional[str] = None,
        position: str = "bottom-right",
        size: tuple = (100, 100),
    ) -> str:
        """
        Add watermark/branding to video.
        
        Args:
            video_path: Source video
            watermark_path: Logo/watermark image
            output_filename: Custom output filename
            position: Position (top-left, top-right, bottom-left, bottom-right)
            size: Watermark size (width, height)
            
        Returns:
            Path to watermarked video
        """
        if not output_filename:
            import uuid
            output_filename = f"{uuid.uuid4}_watermarked.mp4"
        
        output_path = self.output_dir / output_filename
        
        # Position offsets
        positions = {
            "top-left": "x=10:y=10",
            "top-right": "x=W-w-10:y=10",
            "bottom-left": "x=10:y=H-h-10",
            "bottom-right": "x=W-w-10:y=H-h-10",
        }
        
        offset = positions.get(position, positions["bottom-right"])
        
        # Scale watermark
        scale_filter = f"[1:v]scale={size[0]}:{size[1]}[wm]"
        overlay_filter = f"[0:v][wm]overlay={offset}"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", watermark_path,
            "-filter_complex", f"{scale_filter};{overlay_filter}",
            "-c:a", "aac",
            str(output_path),
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            logger.info(f"Added watermark: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Watermark failed: {e}")
            raise
    
    async def concatenate_clips(
        self,
        clip_paths: List[str],
        output_filename: Optional[str] = None,
    ) -> str:
        """
        Concatenate multiple clips into one video.
        
        Args:
            clip_paths: List of clip paths to concatenate
            output_filename: Custom output filename
            
        Returns:
            Path to concatenated video
        """
        if not output_filename:
            import uuid
            output_filename = f"{uuid.uuid4}_concat.mp4"
        
        output_path = self.output_dir / output_filename
        
        # Create concat list file
        concat_list = self.output_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")
        
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264",
            "-c:a", "aac",
            str(output_path),
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            
            logger.info(f"Concatenated {len(clip_paths)} clips: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Concatenation failed: {e}")
            raise
        finally:
            # Cleanup
            if concat_list.exists():
                concat_list.unlink()
    
    async def create_complete_clip(
        self,
        video_path: str,
        clip_definition: Dict[str, Any],
        add_subtitles: bool = True,
        subtitle_path: Optional[str] = None,
        convert_vertical: bool = True,
        watermark_path: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> str:
        """
        Create a complete clip with all processing in one step.
        
        Pipeline:
        1. Extract clip from source
        2. Convert to vertical (optional)
        3. Add subtitles (optional)
        4. Add watermark (optional)
        
        Args:
            video_path: Source video
            clip_definition: Clip details with start/end times
            add_subtitles: Whether to add subtitles
            subtitle_path: Path to subtitle file
            convert_vertical: Convert to 9:16 format
            watermark_path: Logo/watermark path
            output_filename: Custom output filename
            
        Returns:
            Path to final processed clip
        """
        start = clip_definition.get("start", 0)
        end = clip_definition.get("end", start + 30)
        
        # Step 1: Extract clip
        temp_output = self.output_dir / f"temp_{Path(video_path).stem}.mp4"
        
        extracted = await self.extract_clip(
            video_path,
            start,
            end,
            temp_output.name,
            fast_cut=False,  # Use accurate cut
        )
        
        current_video = extracted
        
        # Step 2: Convert to vertical
        if convert_vertical:
            vertical = await self.convert_to_vertical(
                current_video,
                f"vertical_{temp_output.name}",
            )
            current_video = vertical
        
        # Step 3: Add subtitles
        if add_subtitles and subtitle_path:
            subtitled = await self.add_subtitles(
                current_video,
                subtitle_path,
                f"subtitled_{temp_output.name}",
            )
            current_video = subtitled
        
        # Step 4: Add watermark
        if watermark_path:
            final_output = output_filename or f"final_{temp_output.name}"
            watermarked = await self.add_watermark(
                current_video,
                watermark_path,
                final_output,
            )
            current_video = watermarked
        
        logger.info(f"Complete clip created: {current_video}")
        return current_video