"""
Heavy Overlay Editor - Applies transformative edits directly to source footage.

Goal: Make YouTube's ContentID algorithm see the video as "new/different" while
keeping the core footage recognizable to humans.
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class HeavyEditConfig:
    """Configuration for heavy transformative editing."""
    speed_factor: float = 1.08
    audio_pitch_shift: int = 2
    saturation: float = 1.25
    contrast: float = 1.15
    brightness: float = 0.05
    zoom_factor: float = 1.08
    rotation_angle: float = 0.5
    horizontal_shift: int = 20
    vertical_shift: int = 20
    unsharp_amount: float = 1.2
    add_subtitles: bool = True
    add_animated_overlays: bool = True
    overlay_opacity: float = 0.85
    output_width: int = 1080
    output_height: int = 1920
    fps: int = 30


class HeavyOverlayEditor:
    """Applies heavy transformative edits to source footage."""
    
    def __init__(self, output_dir: str = "./outputs/edited"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def apply_heavy_edits(
        self,
        video_path: str,
        config: HeavyEditConfig,
        subtitle_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        overlay_elements: Optional[List[Dict[str, Any]]] = None,
        output_filename: Optional[str] = None,
    ) -> str:
        """Apply ALL transformative edits in a single FFmpeg pass."""
        
        if not output_filename:
            base_name = Path(video_path).stem
            output_filename = f"heavy_edited_{base_name}.mp4"
        
        output_path = self.output_dir / output_filename
        
        # Build filter chain
        filters = []
        
        # Geometric transformations
        zoom = config.zoom_factor
        scaled_width = int(config.output_width * zoom)
        scaled_height = int(config.output_height * zoom)
        
        filters.append(f"scale={scaled_width}:{scaled_height}:force_original_aspect_ratio=decrease")
        filters.append(f"crop={config.output_width}:{config.output_height}")
        
        if config.rotation_angle != 0:
            rotation_rad = config.rotation_angle * 3.14159 / 180
            filters.append(f"rotate={rotation_rad}:ow=expr='hypot(iw,ih)':fillcolor=black")
            filters.append(f"crop={config.output_width*0.95}:{config.output_height*0.95}")
            filters.append(f"scale={config.output_width}:{config.output_height}")
        
        if config.horizontal_shift != 0 or config.vertical_shift != 0:
            filters.append(f"pad={config.output_width*2}:{config.output_height*2}:x={config.output_width//2 + config.horizontal_shift}:y={config.output_height//2 + config.vertical_shift}")
            filters.append(f"crop={config.output_width}:{config.output_height}")
        
        # Color grading
        filters.append(f"eq=saturation={config.saturation}:contrast={config.contrast}:brightness={config.brightness}:gamma=1.0")
        filters.append("colorbalance=rs=0.05:gs=0.02:bs=-0.03:rm=0.02:gm=-0.01:bm=0.01:rh=0.03:gh=-0.02:bh=0.04")
        filters.append(f"unsharp=5:5:{config.unsharp_amount}:5:5:0.0")
        filters.append(f"vignette=PI/4:{config.output_width}/2:{config.output_height}/2:0.3:0.6")
        
        # Overlays
        overlay_filters = []
        if subtitle_path and config.add_subtitles:
            subtitle_escaped = subtitle_path.replace(":", "\\:").replace("'", "'\\''")
            overlay_filters.append(f"subtitles={subtitle_escaped}:force_style='FontSize=24,PrimaryColour=&H00FFFF,Bold=1'")
        
        if overlay_elements and config.add_animated_overlays:
            overlay_filters.extend(self._generate_overlay_filters(overlay_elements, config))
        
        # Combine filters
        if overlay_filters:
            full_filter = ",".join(filters) + "," + ",".join(overlay_filters)
        else:
            full_filter = ",".join(filters)
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", full_filter]
        
        if audio_path and Path(audio_path).exists():
            cmd.extend(["-i", audio_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        
        cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
        cmd.append(str(output_path))
        
        logger.info(f"Applying heavy edits to: {Path(video_path).name}")
        
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Heavy edit processing failed: {error_msg}")
        
        logger.info(f"Heavy edits applied: {output_path}")
        return str(output_path)
    
    def _generate_overlay_filters(self, elements: List[Dict[str, Any]], config: HeavyEditConfig) -> List[str]:
        """Generate FFmpeg filter strings for overlay elements."""
        filters = []
        
        for elem in elements:
            elem_type = elem.get("type")
            
            if elem_type == "arrow":
                start_x = elem.get("start_x", 100)
                start_y = elem.get("start_y", 500)
                end_x = elem.get("end_x", 500)
                end_y = elem.get("end_y", 800)
                color = elem.get("color", "yellow")
                filters.append(f"drawline=x0={start_x}:y0={start_y}:x1={end_x}:y1={end_y}:color={color}:thickness=4")
            
            elif elem_type == "circle":
                center_x = elem.get("x", 540)
                center_y = elem.get("y", 960)
                radius = elem.get("radius", 60)
                color = elem.get("color", "red")
                filters.append(f"drawcircle=x0={center_x}:y0={center_y}:r={radius}:color={color}:thickness=3")
            
            elif elem_type == "text":
                text = elem.get("text", "ANALYSIS").replace("'", "'\\''")
                x = elem.get("x", 50)
                y = elem.get("y", 100)
                fontsize = elem.get("fontsize", 32)
                color = elem.get("color", "white")
                filters.append(f"drawtext=text='{text}':fontsize={fontsize}:fontcolor={color}:x={x}:y={y}:shadowcolor=black:shadowx=2:shadowy=2")
            
            elif elem_type == "box":
                x = elem.get("x", 400)
                y = elem.get("y", 600)
                width = elem.get("width", 200)
                height = elem.get("height", 300)
                color = elem.get("color", "yellow")
                filters.append(f"drawline=x0={x}:y0={y}:x1={x+width}:y1={y}:color={color}:thickness=3")
                filters.append(f"drawline=x0={x+width}:y0={y}:x1={x+width}:y1={y+height}:color={color}:thickness=3")
                filters.append(f"drawline=x0={x+width}:y0={y+height}:x1={x}:y1={y+height}:color={color}:thickness=3")
                filters.append(f"drawline=x0={x}:y0={y+height}:x1={x}:y1={y}:color={color}:thickness=3")
        
        return filters
    
    async def apply_transformative_layers(
        self,
        video_path: str,
        voiceover_path: Optional[str] = None,
        subtitle_path: Optional[str] = None,
        graphics_package: Optional[List[Dict[str, Any]]] = None,
        output_filename: Optional[str] = None,
    ) -> str:
        """Add all transformative layers for fair use."""
        
        config = HeavyEditConfig(
            speed_factor=1.07,
            saturation=1.22,
            contrast=1.14,
            zoom_factor=1.09,
            rotation_angle=0.6,
            add_subtitles=subtitle_path is not None,
        )
        
        overlay_elements = graphics_package or []
        
        if graphics_package:
            overlay_elements.extend([
                {"type": "arrow", "start_x": 200, "start_y": 800, "end_x": 600, "end_y": 600, "color": "cyan", "duration": 2.0},
                {"type": "circle", "x": 540, "y": 960, "radius": 80, "color": "yellow"},
                {"type": "text", "text": "KEY MOMENT", "x": 50, "y": 150, "fontsize": 36, "color": "yellow"},
            ])
        
        return await self.apply_heavy_edits(
            video_path=video_path,
            config=config,
            subtitle_path=subtitle_path,
            audio_path=voiceover_path,
            overlay_elements=overlay_elements,
            output_filename=output_filename,
        )


class ContentIDBypassTest:
    """Tests effectiveness of edits at bypassing ContentID."""
    
    @staticmethod
    async def test_bypass_effectiveness(original_path: str, edited_path: str) -> Dict[str, float]:
        """Test how different the edited version is from original."""
        
        scores = {}
        
        # Frame hash comparison
        hash_diff = await ContentIDBypassTest._compare_frame_hashes(original_path, edited_path)
        scores["frame_hash_divergence"] = hash_diff
        
        # Color histogram correlation
        hist_corr = await ContentIDBypassTest._compare_color_histograms(original_path, edited_path)
        scores["color_histogram_divergence"] = 1 - hist_corr
        
        # Bypass probability
        bypass_probability = scores.get("frame_hash_divergence", 0) * 0.6 + scores.get("color_histogram_divergence", 0) * 0.4
        scores["bypass_probability"] = min(1.0, bypass_probability)
        
        if bypass_probability >= 0.7:
            scores["recommendation"] = "EXCELLENT - Very likely to bypass ContentID"
        elif bypass_probability >= 0.5:
            scores["recommendation"] = "GOOD - Should bypass most automated detection"
        elif bypass_probability >= 0.3:
            scores["recommendation"] = "MODERATE - Consider applying heavier edits"
        else:
            scores["recommendation"] = "POOR - Apply more aggressive transformations"
        
        return scores
    
    @staticmethod
    async def _compare_frame_hashes(original: str, edited: str, num_frames: int = 10) -> float:
        """Compare perceptual hashes of frames."""
        try:
            import imagehash
            from PIL import Image
            
            differences = []
            for i in range(num_frames):
                # Extract frames
                ts_orig = (i + 0.5) * 30 / num_frames
                ts_edit = ts_orig
                
                orig_frame = f"/tmp/orig_frame_{i}.png"
                edit_frame = f"/tmp/edit_frame_{i}.png"
                
                cmd_orig = ["ffmpeg", "-y", "-ss", str(ts_orig), "-i", original, "-vframes", "1", orig_frame]
                cmd_edit = ["ffmpeg", "-y", "-ss", str(ts_edit), "-i", edited, "-vframes", "1", edit_frame]
                
                await asyncio.create_subprocess_exec(*cmd_orig)
                await asyncio.create_subprocess_exec(*cmd_edit)
                
                if Path(orig_frame).exists() and Path(edit_frame).exists():
                    orig_hash = imagehash.phash(Image.open(orig_frame))
                    edit_hash = imagehash.phash(Image.open(edit_frame))
                    diff = orig_hash - edit_hash
                    normalized = diff / 64.0
                    differences.append(normalized)
                    
                    Path(orig_frame).unlink(missing_ok=True)
                    Path(edit_frame).unlink(missing_ok=True)
            
            return sum(differences) / len(differences) if differences else 0.0
        except Exception as e:
            logger.error(f"Frame hash comparison failed: {e}")
            return 0.0
    
    @staticmethod
    async def _compare_color_histograms(original: str, edited: str) -> float:
        """Compare color histograms."""
        try:
            import cv2
            import numpy as np
            
            # Extract single frame from each
            orig_frame = "/tmp/hist_orig.png"
            edit_frame = "/tmp/hist_edit.png"
            
            cmd_orig = ["ffmpeg", "-y", "-ss", "5", "-i", original, "-vframes", "1", orig_frame]
            cmd_edit = ["ffmpeg", "-y", "-ss", "5", "-i", edited, "-vframes", "1", edit_frame]
            
            await asyncio.create_subprocess_exec(*cmd_orig)
            await asyncio.create_subprocess_exec(*cmd_edit)
            
            await asyncio.sleep(1)  # Wait for extraction
            
            if Path(orig_frame).exists() and Path(edit_frame).exists():
                orig_img = cv2.imread(orig_frame)
                edit_img = cv2.imread(edit_frame)
                
                # Compute histograms
                orig_hist = cv2.calcHist([orig_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                edit_hist = cv2.calcHist([edit_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                
                # Compare
                correlation = cv2.compareHist(orig_hist, edit_hist, cv2.HISTCMP_CORRELATION)
                
                Path(orig_frame).unlink(missing_ok=True)
                Path(edit_frame).unlink(missing_ok=True)
                
                return correlation
            return 0.5
        except Exception as e:
            logger.error(f"Color histogram comparison failed: {e}")
            return 0.5