"""
Thumbnail API endpoints.
Create thumbnails for YouTube and Instagram.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional, List
import uuid

from app.thumbnailer.thumbnail_creator import ThumbnailCreator

router = APIRouter()


@router.post("/create")
async def create_thumbnail(
    title: str = Form(..., description="Main title text"),
    subtitle: str = Form("", description="Subtitle text"),
    style: str = Form("bold", description="Style: bold, minimal, dramatic"),
    background: Optional[UploadFile] = File(None, description="Background image"),
    logo: Optional[UploadFile] = File(None, description="Logo/watermark"),
    size: str = Form("youtube", description="Size preset: youtube, instagram, custom"),
    custom_width: int = Form(1280, description="Custom width"),
    custom_height: int = Form(720, description="Custom height"),
):
    """
    Create a thumbnail with uploaded background image.
    
    Returns path to generated thumbnail.
    """
    creator = ThumbnailCreator()
    
    # Handle background
    background_path = None
    if background:
        import tempfile
        
        suffix = Path(background.filename).suffix if background.filename else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            content = await background.read()
            f.write(content)
            background_path = f.name
    
    # Handle logo
    logo_path = None
    if logo:
        import tempfile
        
        suffix = Path(logo.filename).suffix if logo.filename else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            content = await logo.read()
            f.write(content)
            logo_path = f.name
    
    # Determine size
    sizes = {
        "youtube": (1280, 720),
        "instagram": (1080, 1920),
        "youtube_short": (1080, 1920),
        "custom": (custom_width, custom_height),
    }
    
    output_size = sizes.get(size, sizes["youtube"])
    
    try:
        thumbnail_path = await creator.create_thumbnail(
            background_image=background_path or "",
            title=title,
            subtitle=subtitle,
            size=output_size,
            style=style,
            logo_path=logo_path,
        )
        
        return {
            "success": True,
            "thumbnail_path": thumbnail_path,
            "size": output_size,
            "style": style,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        # Cleanup temp files
        if background_path and Path(background_path).exists():
            Path(background_path).unlink()
        if logo_path and Path(logo_path).exists():
            Path(logo_path).unlink()


@router.post("/from-video")
async def create_thumbnail_from_video(
    video_path: str = Form(..., description="Path to video file"),
    title: str = Form(..., description="Main title"),
    subtitle: str = Form("", description="Subtitle"),
    frame_time: float = Form(None, description="Frame time (seconds)"),
    size: str = Form("youtube", description="Size preset"),
    style: str = Form("bold", description="Style"),
    logo_path: Optional[str] = Form(None, description="Logo path"),
):
    """
    Create thumbnail from a video frame.
    
    Automatically extracts frame and creates styled thumbnail.
    """
    creator = ThumbnailCreator()
    
    sizes = {
        "youtube": (1280, 720),
        "instagram": (1080, 1920),
        "custom": None,
    }
    
    output_size = sizes.get(size, (1280, 720))
    
    try:
        thumbnail_path = await creator.create_from_video_frame(
            video_path=video_path,
            frame_time=frame_time or 0,
            title=title,
            subtitle=subtitle,
            size=output_size,
            style=style,
            logo_path=logo_path,
        )
        
        return {
            "success": True,
            "thumbnail_path": thumbnail_path,
            "video_path": video_path,
            "frame_time": frame_time,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/youtube")
async def create_youtube_thumbnail(
    video_path: str = Form(..., description="Path to video"),
    title: str = Form(..., description="Video title"),
    subtitle: str = Form("", description="Subtitle/description"),
    frame_time: float = Form(None, description="Frame to extract"),
    logo_path: Optional[str] = Form(None, description="Channel logo"),
):
    """
    Create YouTube thumbnail (1280x720).
    
    Optimized for YouTube's thumbnail requirements.
    """
    creator = ThumbnailCreator()
    
    try:
        thumbnail_path = await creator.create_youtube_thumbnail(
            video_path=video_path,
            title=title,
            subtitle=subtitle,
            frame_time=frame_time,
            logo_path=logo_path,
        )
        
        return {
            "success": True,
            "thumbnail_path": thumbnail_path,
            "platform": "youtube",
            "dimensions": "1280x720",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/instagram")
async def create_instagram_cover(
    video_path: str = Form(..., description="Path to video"),
    title: str = Form(..., description="Cover title"),
    frame_time: float = Form(None, description="Frame to extract"),
    logo_path: Optional[str] = Form(None, description="Brand logo"),
):
    """
    Create Instagram Reels cover (1080x1920).
    
    Optimized for Instagram Reels/TikTok vertical format.
    """
    creator = ThumbnailCreator()
    
    try:
        thumbnail_path = await creator.create_instagram_cover(
            video_path=video_path,
            title=title,
            frame_time=frame_time,
            logo_path=logo_path,
        )
        
        return {
            "success": True,
            "thumbnail_path": thumbnail_path,
            "platform": "instagram",
            "dimensions": "1080x1920",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/templates")
async def list_templates():
    """List available thumbnail templates."""
    from app.thumbnailer.thumbnail_templates import ThumbnailTemplates
    
    templates = ThumbnailTemplates()
    available = templates.get_available_templates()
    
    return {
        "templates": available,
    }


from pathlib import Path