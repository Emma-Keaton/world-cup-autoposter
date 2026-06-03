"""
Thumbnail Creator - Generate professional thumbnails.
Uses PIL/Pillow for image manipulation.
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from loguru import logger


class ThumbnailCreator:
    """
    Create professional thumbnails for social media.
    
    Supports:
    - YouTube thumbnails (1280x720, 16:9)
    - Instagram Reels covers (1080x1920, 9:16)
    - Custom sizes
    - Text overlays with effects
    - Image composition
    - Branding/watermarks
    """
    
    def __init__(self, output_dir: str = "./outputs/thumbnails"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Font paths (will use system fonts if not found)
        self.font_dir = Path("./assets/fonts")
        self.font_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_thumbnail(
        self,
        background_image: str,
        title: str,
        subtitle: str = "",
        size: Tuple[int, int] = (1280, 720),
        style: str = "bold",
        colors: Optional[Dict[str, str]] = None,
        logo_path: Optional[str] = None,
        extra_text: Optional[List[str]] = None,
    ) -> str:
        """
        Create a complete thumbnail.
        
        Args:
            background_image: Path to background image
            title: Main title text
            subtitle: Subtitle text (optional)
            size: (width, height) tuple
            style: Thumbnail style (bold, minimal, dramatic)
            colors: Color scheme override
            logo_path: Path to logo/watermark
            extra_text: Additional text lines
            
        Returns:
            Path to generated thumbnail
        """
        # Create base image
        img = await self._create_base_image(background_image, size)
        
        # Apply style
        if style == "bold":
            img = self._apply_bold_style(img, colors)
        elif style == "minimal":
            img = self._apply_minimal_style(img, colors)
        elif style == "dramatic":
            img = self._apply_dramatic_style(img, colors)
        
        # Add text overlays
        await self._add_text_layers(
            img,
            title=title,
            subtitle=subtitle,
            extra_text=extra_text or [],
            style=style,
            colors=colors,
        )
        
        # Add logo
        if logo_path:
            await self._add_logo(img, logo_path)
        
        # Add effects
        img = self._add_final_effects(img, style)
        
        # Save
        import uuid
        output_filename = f"thumb_{uuid.uuid4()}.jpg"
        output_path = self.output_dir / output_filename
        
        img.save(output_path, "JPEG", quality=95, optimize=True)
        
        logger.info(f"Created thumbnail: {output_path} ({size[0]}x{size[1]})")
        return str(output_path)
    
    async def _create_base_image(
        self,
        background: str,
        size: Tuple[int, int],
    ) -> Image.Image:
        """Create base image from background or solid color."""
        try:
            img = Image.open(background)
            
            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Resize to fit
            img = self._smart_crop(img, size)
            
            return img
            
        except Exception as e:
            logger.warning(f"Could not load background: {e}, using solid color")
            
            # Create solid color background (football green gradient)
            img = Image.new("RGB", size, "#1a4d2e")
            draw = ImageDraw.Draw(img)
            
            # Add gradient
            for y in range(size[1]):
                r = int(26 + (45 - 26) * y / size[1])
                g = int(77 + (90 - 77) * y / size[1])
                b = int(46 + (63 - 46) * y / size[1])
                draw.line([(0, y), (size[0], y)], fill=(r, g, b))
            
            return img
    
    def _smart_crop(
        self,
        img: Image.Image,
        target_size: Tuple[int, int],
    ) -> Image.Image:
        """Smart crop image to target size (focus on center)."""
        target_w, target_h = target_size
        target_ratio = target_w / target_h
        
        img_w, img_h = img.size
        img_ratio = img_w / img_h
        
        if img_ratio > target_ratio:
            # Image is wider - crop sides
            new_w = int(img_h * target_ratio)
            left = (img_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, img_h))
        else:
            # Image is taller - crop top/bottom
            new_h = int(img_w / target_ratio)
            top = (img_h - new_h) // 2
            img = img.crop((0, top, img_w, top + new_h))
        
        # Resize to exact dimensions
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        return img
    
    def _apply_bold_style(
        self,
        img: Image.Image,
        colors: Optional[Dict[str, str]],
    ) -> Image.Image:
        """Apply bold, high-contrast style."""
        # Enhance saturation
        enhancer = ImageEnhance.Saturation(img)
        img = enhancer.enhance(1.3)
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.4)
        
        # Brighten
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        
        # Add vignette
        img = self._add_vignette(img)
        
        return img
    
    def _apply_minimal_style(
        self,
        img: Image.Image,
        colors: Optional[Dict[str, str]],
    ) -> Image.Image:
        """Apply clean, minimal style."""
        # Slight desaturation
        enhancer = ImageEnhance.Saturation(img)
        img = enhancer.enhance(0.9)
        
        # Soften
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return img
    
    def _apply_dramatic_style(
        self,
        img: Image.Image,
        colors: Optional[Dict[str, str]],
    ) -> Image.Image:
        """Apply dramatic, high-impact style."""
        # High contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.6)
        
        # Darken shadows
        enhancer = ImageEnhance.Shadows(img) if hasattr(ImageEnhance, 'Shadows') else enhancer
        img = enhancer.enhance(0.8)
        
        # Warm color grade
        img = self._apply_color_grade(img, "warm")
        
        return img
    
    async def _add_text_layers(
        self,
        img: Image.Image,
        title: str,
        subtitle: str,
        extra_text: List[str],
        style: str,
        colors: Optional[Dict[str, str]],
    ):
        """Add all text layers to thumbnail."""
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Get fonts
        title_font = self._get_font(size=height // 12, bold=True)
        subtitle_font = self._get_font(size=height // 18)
        extra_font = self._get_font(size=height // 24)
        
        # Color scheme
        if colors is None:
            colors = {
                "title": "#FFFFFF",
                "title_outline": "#000000",
                "subtitle": "#FBBF24",  # Gold
                "subtitle_outline": "#000000",
                "accent": "#22C55E",  # Green
            }
        
        # Title positioning (center)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_h = title_bbox[3] - title_bbox[1]
        
        title_x = (width - title_w) // 2
        title_y = (height - title_h) // 2 - (title_h if subtitle else 0)
        
        # Draw title with outline
        self._draw_text_with_outline(
            draw,
            title,
            (title_x, title_y),
            font=title_font,
            fill=colors["title"],
            outline=colors["title_outline"],
            outline_width=3,
            shadow=True,
        )
        
        # Subtitle
        if subtitle:
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            subtitle_w = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (width - subtitle_w) // 2
            subtitle_y = title_y + title_h + 20
            
            self._draw_text_with_outline(
                draw,
                subtitle,
                (subtitle_x, subtitle_y),
                font=subtitle_font,
                fill=colors["subtitle"],
                outline=colors["subtitle_outline"],
                outline_width=2,
                shadow=True,
            )
        
        # Extra text lines (top/bottom)
        for i, text in enumerate(extra_text[:3]):
            y_pos = 30 + i * 50
            self._draw_text_with_outline(
                draw,
                text,
                (30, y_pos),
                font=extra_font,
                fill="#FFFFFF",
                outline="#000000",
                outline_width=2,
            )
    
    def _draw_text_with_outline(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: Tuple[int, int],
        font: ImageFont.FreeTypeFont,
        fill: str,
        outline: str,
        outline_width: int = 2,
        shadow: bool = False,
    ):
        """Draw text with outline and optional shadow."""
        x, y = position
        
        # Shadow
        if shadow:
            draw.text(
                (x + 3, y + 3),
                text,
                font=font,
                fill="rgba(0,0,0,0.5)",
            )
        
        # Outline (draw multiple times offset)
        for dx in [-outline_width, outline_width, 0]:
            for dy in [-outline_width, outline_width, 0]:
                if dx != 0 or dy != 0:
                    draw.text(
                        (x + dx, y + dy),
                        text,
                        font=font,
                        fill=outline,
                    )
        
        # Main text
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
        )
    
    def _get_font(
        self,
        size: int,
        bold: bool = False,
    ) -> ImageFont.FreeTypeFont:
        """Get font for text rendering."""
        # Try system fonts
        font_names = []
        
        if bold:
            font_names.extend([
                "Arial Black",
                "Arial Bold",
                "Helvetica Bold",
                "Impact",
                "Bebas Neue",
            ])
        else:
            font_names.extend([
                "Arial",
                "Helvetica",
                "Roboto",
            ])
        
        # Try to load font
        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, size)
            except (OSError, IOError):
                continue
        
        # Try local font directory
        if self.font_dir.exists():
            for font_file in self.font_dir.glob("*.ttf"):
                try:
                    return ImageFont.truetype(str(font_file), size)
                except:
                    continue
        
        # Fallback to default
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()
    
    async def _add_logo(
        self,
        img: Image.Image,
        logo_path: str,
        position: str = "bottom-right",
        size: Tuple[int, int] = (120, 120),
    ):
        """Add logo watermark to thumbnail."""
        try:
            logo = Image.open(logo_path)
            
            # Convert to RGBA for transparency
            if logo.mode != "RGBA":
                logo = logo.convert("RGBA")
            
            # Resize logo
            logo = logo.resize(size, Image.Resampling.LANCZOS)
            
            # Position
            img_w, img_h = img.size
            logo_w, logo_h = size
            
            positions = {
                "top-left": (10, 10),
                "top-right": (img_w - logo_w - 10, 10),
                "bottom-left": (10, img_h - logo_h - 10),
                "bottom-right": (img_w - logo_w - 10, img_h - logo_h - 10),
                "center": ((img_w - logo_w) // 2, (img_h - logo_h) // 2),
            }
            
            pos = positions.get(position, positions["bottom-right"])
            
            # Convert main image to RGBA
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            # Paste logo
            img.paste(logo, pos, logo)
            
        except Exception as e:
            logger.warning(f"Could not add logo: {e}")
    
    def _add_vignette(self, img: Image.Image) -> Image.Image:
        """Add vignette effect (darkened edges)."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        width, height = img.size
        
        # Create vignette overlay
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw gradient from edges
        max_radius = max(width, height)
        
        for r in range(int(max_radius / 2), 0, -1):
            alpha = int(128 * (1 - r / (max_radius / 2)))
            if alpha > 0:
                draw.ellipse([
                    (width // 2 - r, height // 2 - r),
                    (width // 2 + r, height // 2 + r)
                ], fill=(0, 0, 0, alpha))
        
        # Composite
        img = Image.alpha_composite(img, overlay)
        
        return img
    
    def _apply_color_grade(
        self,
        img: Image.Image,
        grade: str = "warm",
    ) -> Image.Image:
        """Apply color grading to image."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # Create color overlay
        overlay_color = {
            "warm": (255, 200, 150, 30),
            "cool": (150, 200, 255, 30),
            "dramatic": (255, 100, 50, 20),
            "football": (26, 77, 46, 40),  # Green tint
        }.get(grade, (255, 255, 255, 20))
        
        overlay = Image.new("RGBA", img.size, overlay_color)
        
        # Composite with soft light
        img = Image.alpha_composite(img, overlay)
        
        return img
    
    def _add_final_effects(
        self,
        img: Image.Image,
        style: str,
    ) -> Image.Image:
        """Apply final effects before saving."""
        # Sharpen slightly
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        return img
    
    async def create_from_video_frame(
        self,
        video_path: str,
        frame_time: float,
        title: str,
        subtitle: str = "",
        size: Tuple[int, int] = (1280, 720),
        **kwargs,
    ) -> str:
        """
        Create thumbnail from a specific video frame.
        
        Args:
            video_path: Path to video file
            frame_time: Time in seconds to extract frame
            title: Main title text
            subtitle: Subtitle text
            size: Output size
            **kwargs: Additional args passed to create_thumbnail
            
        Returns:
            Path to thumbnail
        """
        import subprocess
        
        # Extract frame
        temp_frame = self.output_dir / f"frame_{int(frame_time)}.jpg"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(frame_time),
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"scale={size[0]}:{size[1]}",
            str(temp_frame),
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
        
        # Create thumbnail from frame
        thumbnail_path = await self.create_thumbnail(
            background_image=str(temp_frame),
            title=title,
            subtitle=subtitle,
            size=size,
            **kwargs,
        )
        
        # Cleanup temp frame
        temp_frame.unlink()
        
        return thumbnail_path
    
    async def create_youtube_thumbnail(
        self,
        video_path: str,
        title: str,
        subtitle: str = "",
        frame_time: Optional[float] = None,
        logo_path: Optional[str] = None,
    ) -> str:
        """
        Create YouTube thumbnail (1280x720).
        
        Args:
            video_path: Source video
            title: Main title (big text)
            subtitle: Subtitle (smaller)
            frame_time: Frame to extract (default: middle)
            logo_path: Channel logo
            
        Returns:
            Path to YouTube thumbnail
        """
        if frame_time is None:
            # Get video duration and use 1/3 point (often best moment)
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
            duration = float(data.get("format", {}).get("duration", 60))
            frame_time = duration / 3
        
        return await self.create_from_video_frame(
            video_path=video_path,
            frame_time=frame_time,
            title=title,
            subtitle=subtitle,
            size=(1280, 720),
            style="bold",
            logo_path=logo_path,
        )
    
    async def create_instagram_cover(
        self,
        video_path: str,
        title: str,
        frame_time: Optional[float] = None,
        logo_path: Optional[str] = None,
    ) -> str:
        """
        Create Instagram Reels cover (1080x1920, 9:16).
        
        Args:
            video_path: Source video
            title: Main title
            frame_time: Frame to extract
            logo_path: Brand logo
            
        Returns:
            Path to Instagram cover
        """
        if frame_time is None:
            # Use beginning for Reels (hook moment)
            frame_time = 2.0
        
        return await self.create_from_video_frame(
            video_path=video_path,
            frame_time=frame_time,
            title=title,
            subtitle="",
            size=(1080, 1920),
            style="bold",
            logo_path=logo_path,
        )