"""
Batch Processing service for bulk operations.
Processes multiple items in parallel with progress tracking.
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Enum as SQLEnum, Text

from app.core.database import Base, async_session_factory
from app.services.error_notifier import notify_error, ErrorSeverity


class BatchStatus(str, Enum):
    """Batch job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class BatchItem:
    """Individual item in a batch."""
    id: str
    data: Dict
    status: str = "pending"
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class BatchJob:
    """Batch job tracking."""
    id: str
    name: str
    total_items: int
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0


class BatchProcessor:
    """
    Batch processing system for bulk operations.
    
    Features:
    - Parallel item processing
    - Progress tracking
    - Error handling per item
    - Batch status persistence
    """
    
    def __init__(self, max_concurrent: int = 5):
        self._jobs: Dict[str, BatchJob] = {}
        self._items: Dict[str, List[BatchItem]] = {}
        self._max_concurrent = max_concurrent
        logger.info(f"BatchProcessor initialized (max_concurrent={max_concurrent})")
    
    async def create_batch(
        self,
        name: str,
        items: List[Dict],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new batch job.
        
        Args:
            name: Batch job name
            items: List of items to process
            metadata: Optional metadata
        
        Returns:
            Batch job ID
        """
        batch_id = str(uuid.uuid4())
        
        batch_items = [
            BatchItem(id=str(uuid.uuid4()), data=item)
            for item in items
        ]
        
        self._jobs[batch_id] = BatchJob(
            id=batch_id,
            name=name,
            total_items=len(items)
        )
        self._items[batch_id] = batch_items
        
        # Persist to database
        await self._persist_batch(batch_id, name, len(items), metadata)
        
        logger.info(f"Created batch job: {name} with {len(items)} items")
        return batch_id
    
    async def _persist_batch(self, batch_id: str, name: str, count: int, metadata: Optional[Dict]) -> None:
        """Persist batch job to database."""
        async with async_session_factory() as session:
            batch = BatchJobModel(
                id=batch_id,
                name=name,
                total_items=count,
                metadata=metadata or {}
            )
            session.add(batch)
            await session.commit()
    
    async def process_batch(
        self,
        batch_id: str,
        processor: Callable[[Dict], Awaitable[Any]],
        progress_callback: Optional[Callable[[BatchJob], None]] = None
    ) -> BatchJob:
        """
        Process all items in a batch.
        
        Args:
            batch_id: Batch job ID
            processor: Async function to process each item
            progress_callback: Optional callback for progress updates
        
        Returns:
            Completed batch job
        """
        if batch_id not in self._jobs:
            raise ValueError(f"Batch job not found: {batch_id}")
        
        job = self._jobs[batch_id]
        items = self._items[batch_id]
        
        job.status = BatchStatus.PROCESSING
        
        # Process items with concurrency limit
        semaphore = asyncio.Semaphore(self._max_concurrent)
        
        async def process_item(item: BatchItem) -> None:
            async with semaphore:
                try:
                    result = await processor(item.data)
                    item.status = "success"
                    item.result = result
                    job.succeeded += 1
                except Exception as e:
                    item.status = "failed"
                    item.error = str(e)
                    job.failed += 1
                    logger.error(f"Batch item failed: {e}")
                
                job.processed += 1
                job.progress_percent = (job.processed / job.total_items) * 100
                
                # Update progress
                if progress_callback:
                    progress_callback(job)
                
                # Update database
                await self._update_batch_progress(batch_id, job)
        
        # Process all items
        tasks = [process_item(item) for item in items]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Finalize
        job.completed_at = datetime.now()
        if job.failed == 0:
            job.status = BatchStatus.COMPLETED
        elif job.succeeded == 0:
            job.status = BatchStatus.FAILED
        else:
            job.status = BatchStatus.PARTIAL
        
        logger.info(f"Batch job completed: {job.succeeded}/{job.total_items} succeeded")
        return job
    
    async def _update_batch_progress(self, batch_id: str, job: BatchJob) -> None:
        """Update batch progress in database."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BatchJobModel).where(BatchJobModel.id == batch_id)
            )
            batch = result.scalar_one_or_none()
            
            if batch:
                batch.processed = job.processed
                batch.succeeded = job.succeeded
                batch.failed = job.failed
                batch.progress_percent = job.progress_percent
                batch.status = job.status.value
                await session.commit()
    
    async def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """Get current batch status."""
        if batch_id in self._jobs:
            return self._jobs[batch_id]
        
        # Try to load from database
        async with async_session_factory() as session:
            result = await session.execute(
                select(BatchJobModel).where(BatchJobModel.id == batch_id)
            )
            batch = result.scalar_one_or_none()
            
            if batch:
                return BatchJob(
                    id=batch.id,
                    name=batch.name,
                    total_items=batch.total_items,
                    processed=batch.processed,
                    succeeded=batch.succeeded,
                    failed=batch.failed,
                    status=BatchStatus(batch.status),
                    created_at=batch.created_at,
                    completed_at=batch.completed_at,
                    progress_percent=batch.progress_percent
                )
        
        return None
    
    async def list_batches(self, limit: int = 20) -> List[Dict]:
        """List recent batch jobs."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BatchJobModel)
                .order_by(BatchJobModel.created_at.desc())
                .limit(limit)
            )
            batches = result.scalars().all()
            
            return [
                {
                    "id": b.id,
                    "name": b.name,
                    "status": b.status,
                    "progress": f"{b.processed}/{b.total_items}",
                    "created_at": b.created_at.isoformat()
                }
                for b in batches
            ]
    
    async def get_batch_results(self, batch_id: str) -> List[Dict]:
        """Get results for all items in a batch."""
        if batch_id not in self._items:
            return []
        
        return [
            {
                "id": item.id,
                "status": item.status,
                "result": item.result,
                "error": item.error
            }
            for item in self._items[batch_id]
        ]


class BatchJobModel(Base):
    """Database model for batch jobs."""
    
    __tablename__ = "batch_jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(SQLEnum(BatchStatus), default=BatchStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default='now()')
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    job_metadata: Mapped[Dict] = mapped_column(String, default="{}")


# Global instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get the global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
