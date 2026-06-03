"""
Asset downloader for stock footage and images.
Integrates with Pexels and Pixabay APIs.
"""
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core.config import settings
from app.core.utils import sanitize_filename


class AssetDownloader:
    """
    Downloads stock footage and images for video generation.
    
    Integrates with Pexels and Pixabay APIs to find relevant
    football/soccer visual assets.
    """
    
    def __init__(self, output_dir: str = "./temp/assets"):
        """
        Initialize asset downloader.
        
        Args:
            output_dir: Directory for downloaded assets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.pexels_api_key = settings.PEXELS_API_KEY
        self.pixabay_api_key = settings.PIXABAY_API_KEY
    
    async def search_pexels(
        self,
        query: str,
        orientation: str = "portrait",
        size: str = "small",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Pexels for videos/images.
        
        Args:
            query: Search query
            orientation: portrait, landscape, or square
            size: small, medium, large
            limit: Maximum results
            
        Returns:
            List of asset metadata
        """
        if not self.pexels_api_key:
            logger.warning("Pexels API key not configured")
            return []
        
        headers = {
            "Authorization": self.pexels_api_key,
        }
        
        params = {
            "query": query,
            "orientation": orientation,
            "size": size,
            "per_page": min(limit, 80),  # Pexels max per page
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search videos
                response = await client.get(
                    "https://api.pexels.com/videos/search",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                for video in data.get("videos", [])[:limit]:
                    video_files = video.get("video_files", [])
                    
                    # Find best quality file
                    best_file = None
                    for vf in sorted(video_files, key=lambda x: x.get("width", 0), reverse=True):
                        if vf.get("width", 0) <= 1080:  # Max 1080 width
                            best_file = vf
                            break
                    
                    if not best_file and video_files:
                        best_file = video_files[0]
                    
                    results.append({
                        "source": "pexels",
                        "type": "video",
                        "id": video.get("id"),
                        "url": best_file.get("link") if best_file else None,
                        "thumbnail": video.get("image"),
                        "width": best_file.get("width"),
                        "height": best_file.get("height"),
                        "duration": video.get("duration"),
                        "photographer": video.get("photographer"),
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Pexels search failed: {e}")
            return []
    
    async def search_pixabay(
        self,
        query: str,
        media_type: str = "video",
        orientation: str = "vertical",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Pixabay for videos/images.
        
        Args:
            query: Search query
            media_type: video, image, or illustration
            orientation: vertical, horizontal, or all
            limit: Maximum results
            
        Returns:
            List of asset metadata
        """
        if not self.pixabay_api_key:
            logger.warning("Pixabay API key not configured")
            return []
        
        params = {
            "key": self.pixabay_api_key,
            "q": query,
            "orientation": orientation,
            "image_type": media_type if media_type != "video" else "all",
            "per_page": min(limit, 100),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if media_type == "video":
                    endpoint = "https://pixabay.com/api/videos/"
                else:
                    endpoint = "https://pixabay.com/api/"
                
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                for item in data.get("hits", [])[:limit]:
                    if media_type == "video":
                        # Get videos
                        videos = item.get("videos", {})
                        small = videos.get("small", {})
                        results.append({
                            "source": "pixabay",
                            "type": "video",
                            "id": item.get("id"),
                            "url": small.get("url"),
                            "thumbnail": item.get("thumbnails", {}).get("small"),
                            "width": small.get("width"),
                            "height": small.get("height"),
                            "duration": item.get("duration"),
                            "user": item.get("user"),
                        })
                    else:
                        # Get images
                        results.append({
                            "source": "pixabay",
                            "type": "image",
                            "id": item.get("id"),
                            "url": item.get("webformatURL"),
                            "thumbnail": item.get("previewURL"),
                            "width": item.get("imageWidth"),
                            "height": item.get("imageHeight"),
                            "user": item.get("user"),
                        })
                
                return results
                
        except Exception as e:
            logger.error(f"Pixabay search failed: {e}")
            return []
    
    async def download_asset(
        self,
        asset: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Download an asset to local storage.
        
        Args:
            asset: Asset metadata from search
            output_filename: Custom filename
            
        Returns:
            Path to downloaded file or None
        """
        url = asset.get("url")
        if not url:
            logger.warning("No URL for asset")
            return None
        
        if not output_filename:
            source = asset.get("source", "unknown")
            asset_id = asset.get("id", "unknown")
            ext = "mp4" if asset.get("type") == "video" else "jpg"
            output_filename = f"{source}_{asset_id}.{ext}"
        
        output_path = self.output_dir / sanitize_filename(output_filename)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded asset: {output_path}")
                return str(output_path)
                
        except Exception as e:
            logger.error(f"Asset download failed: {e}")
            return None
    
    async def search_football_assets(
        self,
        context: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for football-related assets based on context.
        
        Args:
            context: Content context/topic
            limit: Maximum results
            
        Returns:
            List of relevant assets
        """
        # Generate search queries based on context
        base_queries = [
            "football soccer",
            "stadium crowd",
            "football player",
            "soccer match",
            "world cup",
        ]
        
        # Add context-specific queries
        context_terms = context.lower().split()[:5]
        context_queries = [f"football {term}" for term in context_terms if len(term) > 3]
        
        all_queries = base_queries + context_queries
        
        all_assets = []
        
        # Search both APIs
        for query in all_queries[:5]:  # Limit queries to avoid rate limits
            pexels_results = await self.search_pexels(query, limit=limit // 2)
            pixabay_results = await self.search_pixabay(query, limit=limit // 2)
            
            all_assets.extend(pexels_results)
            all_assets.extend(pixabay_results)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_assets = []
        for asset in all_assets:
            url = asset.get("url")
            if url and url not in seen_urls:
                unique_assets.append(asset)
                seen_urls.add(url)
        
        return unique_assets[:limit]
    
    async def download_batch(
        self,
        assets: List[Dict[str, Any]],
        prefix: Optional[str] = None
    ) -> List[str]:
        """
        Download multiple assets concurrently.
        
        Args:
            assets: List of assets to download
            prefix: Filename prefix
            
        Returns:
            List of downloaded file paths
        """
        tasks = []
        
        for i, asset in enumerate(assets):
            ext = "mp4" if asset.get("type") == "video" else "jpg"
            filename = f"{prefix}_{i}.{ext}" if prefix else None
            task = self.download_asset(asset, filename)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        paths = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch download error: {result}")
            elif result:
                paths.append(result)
        
        return paths


import asyncio