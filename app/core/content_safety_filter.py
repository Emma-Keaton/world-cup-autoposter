"""
Content Safety Filter - Replaces pride/LGBTQ/rainbow symbols with cross.

Detects and replaces ONLY:
- LGBTQ+ pride flags (rainbow flags)
- Rainbow color schemes (6+ rainbow colors)
- Pride symbols

Does NOT touch:
- FIFA logo (allowed)
- World Cup branding (allowed)  
- Sponsor logos (allowed)
- Any other content

Replacement: Cross symbol
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from loguru import logger

from PIL import Image, ImageDraw


@dataclass
class DetectionResult:
    has_pride_symbols: bool
    detected_items: List[str]
    confidence: float
    frame_timestamps: List[float]
    requires_replacement: bool


class ContentSafetyFilter:
    """Scans for and replaces pride/LGBTQ/rainbow symbols with cross."""
    
    def __init__(self):
        self.detection_cache: Dict[str, DetectionResult] = {}
    
    async def scan_video(self, video_path: str) -> DetectionResult:
        """Scan video for pride/rainbow symbols only."""
        if video_path in self.detection_cache:
            return self.detection_cache[video_path]
        
        logger.info(f"Scanning for pride/rainbow symbols: {video_path}")
        
        # Get video duration
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        duration = float(data.get("format", {}).get("duration", 30))
        
        # Extract frames every 2 seconds
        num_frames = max(1, int(duration / 2))
        
        detected_items = []
        frame_timestamps = []
        max_confidence = 0.0
        
        for i in range(num_frames):
            ts = (i + 0.5) * 2
            frame_path = Path(f"/tmp/pride_scan_{i:04d}.jpg")
            
            # Extract frame
            cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", video_path, "-vframes", "1", str(frame_path)]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            
            if frame_path.exists():
                result = await self._scan_frame(str(frame_path))
                if result["has_pride"]:
                    detected_items.extend(result["items"])
                    frame_timestamps.append(ts)
                    max_confidence = max(max_confidence, result["confidence"])
                frame_path.unlink()
        
        result = DetectionResult(
            has_pride_symbols=len(detected_items) > 0,
            detected_items=list(set(detected_items)),
            confidence=max_confidence,
            frame_timestamps=frame_timestamps,
            requires_replacement=max_confidence > 0.5,
        )
        
        self.detection_cache[video_path] = result
        
        if result.has_pride_symbols:
            logger.warning(f"🏳️‍🌈 Detected pride/rainbow symbols: {result.detected_items}")
        else:
            logger.info("✅ No pride/rainbow symbols detected")
        
        return result
    
    async def _scan_frame(self, frame_path: str) -> Dict[str, Any]:
        """Scan single frame for rainbow/pride colors."""
        try:
            img = Image.open(frame_path)
            pixels = list(img.getdata())
            total = len(pixels)
            
            # Rainbow colors (RGB)
            rainbow = [
                (255, 0, 0),      # Red
                (255, 127, 0),    # Orange
                (255, 255, 0),    # Yellow
                (0, 255, 0),      # Green
                (0, 127, 255),    # Blue
                (128, 0, 128),    # Purple
            ]
            
            # Count pixels matching each rainbow color
            color_counts = [0] * 6
            
            for px in pixels:
                r, g, b = px[:3]
                for i, (cr, cg, cb) in enumerate(rainbow):
                    if abs(r - cr) < 60 and abs(g - cg) < 60 and abs(b - cb) < 60:
                        color_counts[i] += 1
            
            # Check if all 6 rainbow colors are significantly present
            threshold = total * 0.005  # 0.5% of image
            present = sum(1 for c in color_counts if c > threshold)
            
            detected = []
            confidence = 0.0
            
            if present >= 5:
                # Strong rainbow pattern detected
                detected.append("rainbow_flag")
                confidence = present / 6.0
                
                # Check for horizontal banding (flag pattern)
                if self._detect_horizontal_bands(img, rainbow):
                    detected.append("pride_flag_horizontal")
                    confidence = min(1.0, confidence + 0.2)
            
            return {
                "has_pride": len(detected) > 0,
                "items": detected,
                "confidence": confidence,
            }
            
        except Exception as e:
            logger.error(f"Frame scan error: {e}")
            return {"has_pride": False, "items": [], "confidence": 0.0}
    
    def _detect_horizontal_bands(self, img: Image.Image, rainbow: List[tuple]) -> bool:
        """Detect if rainbow colors are arranged in horizontal bands (flag pattern)."""
        w, h = img.size
        pixels = img.load()
        
        # Sample horizontal strips
        num_strips = 6
        strip_height = h // num_strips
        
        for i, (cr, cg, cb) in enumerate(rainbow):
            strip_y = i * strip_height + strip_height // 2
            
            # Count matching pixels in this strip
            match_count = 0
            for x in range(0, w, 10):  # Sample every 10th pixel
                px = pixels[x, strip_y]
                if abs(px[0] - cr) < 60 and abs(px[1] - cg) < 60 and abs(px[2] - cb) < 60:
                    match_count += 1
            
            # Each strip should have significant matching color
            if match_count < w / 10 / 3:  # Less than 1/3 match
                return False
        
        return True
    
    async def replace_with_cross(
        self,
        video_path: str,
        output_path: str,
        detection: DetectionResult,
    ) -> str:
        """Replace detected pride/rainbow symbols with cross."""
        
        if not detection.has_pride_symbols:
            logger.info("No pride symbols to replace, copying original")
            import shutil
            shutil.copy(video_path, output_path)
            return output_path
        
        logger.info(f"✝️ Replacing {len(detection.detected_items)} pride symbols with cross")
        
        # Get video info
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        duration = float(data.get("format", {}).get("duration", 30))
        
        # Get FPS
        fps_cmd = ["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video_path]
        proc = await asyncio.create_subprocess_exec(*fps_cmd, stdout=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        fps = eval(stdout.decode().strip()) if stdout else 30
        
        # Extract all frames
        frames_dir = Path("/tmp/pride_replace")
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        await (await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", video_path, str(frames_dir / "frame_%05d.png")
        )).communicate()
        
        # Create cross overlay
        cross = self._create_cross_overlay(256, 256)
        
        # Modify frames at detected timestamps
        frame_dur = 1.0 / fps
        frames_to_modify = [int(ts / frame_dur) for ts in detection.frame_timestamps]
        
        modified = 0
        for fn in frames_to_modify:
            fp = frames_dir / f"frame_{fn:05d}.png"
            if fp.exists():
                await self._overlay_cross_on_rainbow(str(fp), cross)
                modified += 1
        
        logger.info(f"Modified {modified} frames with cross overlay")
        
        # Re-encode video
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-i", video_path, "-c:a", "copy",
            output_path,
        ]
        
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.communicate()
        
        # Cleanup
        for f in frames_dir.glob("*.png"):
            f.unlink()
        
        logger.info(f"✅ Clean video saved: {output_path}")
        return output_path
    
    def _create_cross_overlay(self, w: int, h: int) -> Image.Image:
        """Create white cross with black outline on transparent background."""
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Dimensions
        bar_w = w // 12
        bar_h = h // 3
        cx, cy = w // 2, h // 2
        
        # White cross (vertical + horizontal bars)
        # Vertical
        draw.rectangle(
            [cx - bar_w//2, cy - bar_h//2, cx + bar_w//2, cy + bar_h//2],
            fill=(255, 255, 255, 255)
        )
        # Horizontal
        draw.rectangle(
            [cx - bar_h//2, cy - bar_w//2, cx + bar_h//2, cy + bar_w//2],
            fill=(255, 255, 255, 255)
        )
        
        # Black outline
        draw.rectangle(
            [cx - bar_w//2 - 2, cy - bar_h//2 - 2, cx + bar_w//2 + 2, cy + bar_h//2 + 2],
            outline=(0, 0, 0, 255),
            width=2
        )
        draw.rectangle(
            [cx - bar_h//2 - 2, cy - bar_w//2 - 2, cx + bar_h//2 + 2, cy + bar_w//2 + 2],
            outline=(0, 0, 0, 255),
            width=2
        )
        
        return img
    
    async def _overlay_cross_on_rainbow(self, frame_path: str, cross: Image.Image):
        """Overlay cross on rainbow-colored regions of frame."""
        try:
            img = Image.open(frame_path).convert("RGBA")
            w, h = img.size
            
            # Find rainbow-colored regions
            pixels = list(img.getdata())
            rainbow = [
                (255, 0, 0), (255, 127, 0), (255, 255, 0),
                (0, 255, 0), (0, 127, 255), (128, 0, 128),
            ]
            
            # Find bounding box of rainbow regions
            rainbow_positions = []
            for idx, px in enumerate(pixels):
                r, g, b = px[:3]
                for cr, cg, cb in rainbow:
                    if abs(r - cr) < 60 and abs(g - cg) < 60 and abs(b - cb) < 60:
                        x = idx % w
                        y = idx // w
                        rainbow_positions.append((x, y))
                        break
            
            if rainbow_positions:
                # Calculate center of rainbow region
                avg_x = sum(p[0] for p in rainbow_positions) // len(rainbow_positions)
                avg_y = sum(p[1] for p in rainbow_positions) // len(rainbow_positions)
                
                # Resize cross to cover region
                region_w = max(p[0] for p in rainbow_positions) - min(p[0] for p in rainbow_positions) + 1
                region_h = max(p[1] for p in rainbow_positions) - min(p[1] for p in rainbow_positions) + 1
                cross_size = max(region_w, region_h, 64)
                cross_resized = cross.resize((cross_size, cross_size))
                
                # Paste cross centered on rainbow region
                paste_x = avg_x - cross_size // 2
                paste_y = avg_y - cross_size // 2
                
                img.paste(cross_resized, (paste_x, paste_y), cross_resized)
                
                img.save(frame_path)
                
        except Exception as e:
            logger.error(f"Cross overlay failed: {e}")
    
    async def generate_safe_prompts(
        self,
        original_prompts: List[str],
        detection: DetectionResult,
    ) -> List[str]:
        """Modify generation prompts to avoid creating pride/rainbow content."""
        
        if not detection.has_pride_symbols:
            return original_prompts
        
        safe_prompts = []
        
        # Insert critical instruction at start
        safe_prompts.append(
            "CRITICAL INSTRUCTION: Use CROSS symbol. NO rainbow colors. NO pride flags. "
            "NO LGBTQ+ symbolism. Traditional colors only (red, white, blue, green, black, gold). "
            "Replace any rainbow patterns with cross imagery."
        )
        
        # Modify each prompt
        for prompt in original_prompts:
            safe = prompt.lower()
            
            # Replace problematic terms
            replacements = {
                "rainbow": "cross",
                "pride": "faith",
                "diverse colors": "bold colors",
                "inclusive": "unified",
                "lgbt": "football",
            }
            
            for orig, repl in replacements.items():
                safe = safe.replace(orig, repl)
            
            safe += " Use cross symbol. NO rainbow. NO pride colors."
            safe_prompts.append(safe)
        
        return safe_prompts