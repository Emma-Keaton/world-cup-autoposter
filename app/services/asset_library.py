"""
Asset Library for storing and reusing brand assets.
Manages logos, watermarks, intros, outros, music, and templates.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Enum as SQLEnum

from app.core.database import Base, async_session_factory
from app.core.config import settings


class AssetType(str, Enum):
    """Types of assets in the library."""
    LOGO = "logo"
    WATERMARK = "watermark"
    INTRO_VIDEO = "intro_video"
    OUTRO_VIDEO = "outro_video"
    BACKGROUND_MUSIC = "background_music"
    TRANSITION = "transition"
    TEMPLATE = "template"
    FONT = "font"
    COLOR_PALETTE = "color_palette"


@dataclass
class Asset:
    """Asset data class."""
    id: str
    name: str
    asset_type: AssetType
    file_path: str
    file_size: int
    created_at: datetime
    is_default: bool
    metadata: Dict


class AssetLibrary:
    """
    Digital asset management system.
    
    Features:
    - Store reusable brand assets
    - Default asset selection
    - Asset metadata tracking
    - File size optimization
    """
    
    def __init__(self):
        self.assets_dir = Path(__file__).parent.parent.parent / "assets" / "library"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"AssetLibrary initialized at {self.assets_dir}")
    
    async def save_asset(
        self,
        name: str,
        asset_type: AssetType,
        file_path: str,
        file_size: int = 0,
        is_default: bool = False,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save an asset to the library.
        
        Args:
            name: Asset name
            asset_type: Type of asset
            file_path: Path to the asset file
            file_size: File size in bytes
            is_default: Whether this is the default asset for its type
            metadata: Additional metadata
        
        Returns:
            Asset ID
        """
        asset_id = str(uuid.uuid4())
        
        # Copy file to library
        source_path = Path(file_path)
        if source_path.exists():
            ext = source_path.suffix
            dest_path = self.assets_dir / f"{asset_type.value}_{asset_id}{ext}"
            dest_path.write_bytes(source_path.read_bytes())
            file_size = dest_path.stat().st_size
        
        async with async_session_factory() as session:
            # If this is default, unset other defaults for this type
            if is_default:
                await session.execute(
                    delete(AssetModel).where(
                        AssetModel.asset_type == asset_type,
                        AssetModel.is_default == True
                    )
                )
            
            # Create new asset
            asset = AssetModel(
                id=asset_id,
                name=name,
                asset_type=asset_type,
                file_path=str(dest_path if 'dest_path' in locals() else file_path),
                file_size=file_size,
                is_default=is_default,
                metadata=metadata or {}
            )
            
            session.add(asset)
            await session.commit()
        
        logger.info(f"Saved asset: {name} ({asset_type.value})")
        return asset_id
    
    async def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(AssetModel).where(AssetModel.id == asset_id)
            )
            asset = result.scalar_one_or_none()
            
            if asset:
                return Asset(
                    id=asset.id,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    file_path=asset.file_path,
                    file_size=asset.file_size,
                    created_at=asset.created_at,
                    is_default=asset.is_default,
                    metadata=asset.metadata
                )
        return None
    
    async def get_assets_by_type(self, asset_type: AssetType) -> List[Asset]:
        """Get all assets of a specific type."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(AssetModel)
                .where(AssetModel.asset_type == asset_type)
                .order_by(AssetModel.is_default.desc(), AssetModel.created_at.desc())
            )
            assets = result.scalars().all()
            
            return [
                Asset(
                    id=a.id,
                    name=a.name,
                    asset_type=a.asset_type,
                    file_path=a.file_path,
                    file_size=a.file_size,
                    created_at=a.created_at,
                    is_default=a.is_default,
                    metadata=a.metadata
                )
                for a in assets
            ]
    
    async def get_default_asset(self, asset_type: AssetType) -> Optional[Asset]:
        """Get the default asset for a type."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(AssetModel)
                .where(
                    AssetModel.asset_type == asset_type,
                    AssetModel.is_default == True
                )
            )
            asset = result.scalar_one_or_none()
            
            if asset:
                return Asset(
                    id=asset.id,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    file_path=asset.file_path,
                    file_size=asset.file_size,
                    created_at=asset.created_at,
                    is_default=asset.is_default,
                    metadata=asset.metadata
                )
        return None
    
    async def list_all_assets(self) -> Dict[str, List[Asset]]:
        """List all assets grouped by type."""
        all_assets = {}
        for asset_type in AssetType:
            assets = await self.get_assets_by_type(asset_type)
            if assets:
                all_assets[asset_type.value] = assets
        return all_assets
    
    async def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset from the library."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(AssetModel).where(AssetModel.id == asset_id)
            )
            asset = result.scalar_one_or_none()
            
            if asset:
                # Delete file
                file_path = Path(asset.file_path)
                if file_path.exists():
                    file_path.unlink()
                
                # Delete from DB
                await session.delete(asset)
                await session.commit()
                
                logger.info(f"Deleted asset: {asset.name}")
                return True
        
        return False
    
    async def get_library_stats(self) -> Dict:
        """Get asset library statistics."""
        stats = {
            "total_assets": 0,
            "total_size_bytes": 0,
            "by_type": {}
        }
        
        async with async_session_factory() as session:
            result = await session.execute(select(AssetModel))
            assets = result.scalars().all()
            
            stats["total_assets"] = len(assets)
            stats["total_size_bytes"] = sum(a.file_size for a in assets)
            
            for asset_type in AssetType:
                type_assets = [a for a in assets if a.asset_type == asset_type]
                stats["by_type"][asset_type.value] = {
                    "count": len(type_assets),
                    "size_bytes": sum(a.file_size for a in type_assets)
                }
        
        return stats


class AssetModel(Base):
    """Database model for assets."""
    
    __tablename__ = "assets"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default='now()')
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    asset_metadata: Mapped[Dict] = mapped_column(String, default="{}")  # Store as JSON string


# Global instance
_asset_library: Optional[AssetLibrary] = None


def get_asset_library() -> AssetLibrary:
    """Get the global asset library instance."""
    global _asset_library
    if _asset_library is None:
        _asset_library = AssetLibrary()
    return _asset_library