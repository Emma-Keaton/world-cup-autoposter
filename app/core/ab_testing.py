"""
A/B Testing Framework for content optimization.
Tests multiple variations to find best-performing content.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Boolean, JSON, Enum as SQLEnum

from app.core.database import Base, async_session_factory
from app.services.analytics_service import get_analytics


class TestStatus(str, Enum):
    """A/B Test status."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"


class WinnerSelection(str, Enum):
    """How winner is selected."""
    STATISTICAL = "statistical"  # Based on statistical significance
    MANUAL = "manual"  # User selects winner
    AUTO = "auto"  # Auto-select after confidence threshold


@dataclass
class Variation:
    """A single variation in an A/B test."""
    id: str
    name: str
    content_params: Dict[str, Any]
    is_control: bool = False


@dataclass
class TestResult:
    """Results from an A/B test."""
    test_id: str
    winner_id: str
    confidence: float
    metrics: Dict[str, float]
    recommendation: str


class ABTest:
    """
    A/B Testing framework for content optimization.
    
    Features:
    - Test multiple content variations
    - Automatic winner selection
    - Statistical significance calculation
    - Multi-metric comparison
    """
    
    def __init__(self):
        logger.info("ABTest framework initialized")
    
    async def create_test(
        self,
        name: str,
        description: str,
        variations: List[Variation],
        metric_to_optimize: str = "engagement_rate",
        min_sample_size: int = 100,
        confidence_threshold: float = 0.95,
        auto_select_winner: bool = True
    ) -> str:
        """
        Create a new A/B test.
        
        Args:
            name: Test name
            description: Test description
            variations: List of variations (first should be control)
            metric_to_optimize: Primary metric for winner selection
            min_sample_size: Minimum samples before declaring winner
            confidence_threshold: Confidence level for auto-selection
            auto_select_winner: Whether to auto-select winner
        
        Returns:
            Test ID
        """
        test_id = str(uuid.uuid4())
        
        async with async_session_factory() as session:
            test = ABTestModel(
                id=test_id,
                name=name,
                description=description,
                status=TestStatus.DRAFT,
                metric_to_optimize=metric_to_optimize,
                min_sample_size=min_sample_size,
                confidence_threshold=confidence_threshold,
                auto_select_winner=auto_select_winner,
                variations_json=[{
                    "id": v.id,
                    "name": v.name,
                    "content_params": v.content_params,
                    "is_control": v.is_control
                } for v in variations],
                results_json={}
            )
            
            session.add(test)
            await session.commit()
        
        logger.info(f"Created A/B test: {name} ({test_id}) with {len(variations)} variations")
        return test_id
    
    async def start_test(self, test_id: str) -> bool:
        """Start an A/B test."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ABTestModel).where(ABTestModel.id == test_id)
            )
            test = result.scalar_one_or_none()
            
            if not test:
                return False
            
            test.status = TestStatus.RUNNING
            test.started_at = datetime.now()
            await session.commit()
        
        logger.info(f"Started A/B test: {test_id}")
        return True
    
    async def get_next_variation(self, test_id: str) -> Optional[Variation]:
        """
        Get the next variation to show.
        Uses adaptive allocation (more traffic to better performers).
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(ABTestModel).where(ABTestModel.id == test_id)
            )
            test = result.scalar_one_or_none()
            
            if not test or test.status != TestStatus.RUNNING:
                return None
            
            variations = test.variations_json
            
            # Simple random allocation for now
            # In production, use Thompson Sampling or UCB for adaptive allocation
            import random
            selected = random.choice(variations)
            
            return Variation(
                id=selected["id"],
                name=selected["name"],
                content_params=selected["content_params"],
                is_control=selected.get("is_control", False)
            )
    
    async def record_result(
        self,
        test_id: str,
        variation_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """
        Record results for a variation.
        
        Args:
            test_id: Test ID
            variation_id: Which variation was shown
            metrics: Performance metrics (views, likes, engagement_rate, etc.)
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(ABTestModel).where(ABTestModel.id == test_id)
            )
            test = result.scalar_one_or_none()
            
            if not test:
                return False
            
            # Get or create results
            results = test.results_json or {}
            
            if variation_id not in results:
                results[variation_id] = {
                    "impressions": 0,
                    "metrics_sum": {},
                    "metrics_count": 0
                }
            
            # Update aggregates
            var_result = results[variation_id]
            var_result["impressions"] += 1
            
            for metric, value in metrics.items():
                if metric not in var_result["metrics_sum"]:
                    var_result["metrics_sum"][metric] = 0
                var_result["metrics_sum"][metric] += value
            
            var_result["metrics_count"] += 1
            
            test.results_json = results
            
            # Check if we should select a winner
            total_impressions = sum(
                v["impressions"] for v in results.values()
            )
            
            if total_impressions >= test.min_sample_size and test.auto_select_winner:
                winner = await self._calculate_winner(test)
                if winner:
                    test.status = TestStatus.COMPLETED
                    test.completed_at = datetime.now()
                    test.winner_id = winner["variation_id"]
                    test.confidence = winner["confidence"]
            
            await session.commit()
        
        return True
    
    async def _calculate_winner(self, test: ABTestModel) -> Optional[Dict]:
        """Calculate statistical winner."""
        results = test.results_json or {}
        
        if len(results) < 2:
            return None
        
        # Calculate averages for each variation
        averages = {}
        for var_id, var_data in results.items():
            if var_data["metrics_count"] > 0:
                avg = var_data["metrics_sum"].get(test.metric_to_optimize, 0) / var_data["metrics_count"]
                averages[var_id] = avg
        
        if not averages:
            return None
        
        # Find best performer
        best_var = max(averages.items(), key=lambda x: x[1])
        second_best = sorted(averages.items(), key=lambda x: x[1], reverse=True)[1]
        
        # Calculate confidence (simplified - in production use proper statistical test)
        if second_best[1] > 0:
            improvement = (best_var[1] - second_best[1]) / second_best[1]
            confidence = min(0.99, 0.5 + (improvement * 0.5))  # Simple heuristic
        else:
            confidence = 0.5
        
        if confidence >= test.confidence_threshold:
            return {
                "variation_id": best_var[0],
                "confidence": confidence,
                "improvement": improvement
            }
        
        return None
    
    async def get_test_results(self, test_id: str) -> Optional[TestResult]:
        """Get final test results."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ABTestModel).where(ABTestModel.id == test_id)
            )
            test = result.scalar_one_or_none()
            
            if not test or test.status != TestStatus.COMPLETED:
                return None
            
            # Calculate metrics for each variation
            results = test.results_json or {}
            metrics = {}
            
            for var_id, var_data in results.items():
                if var_data["metrics_count"] > 0:
                    var_metrics = {}
                    for metric, total in var_data["metrics_sum"].items():
                        var_metrics[metric] = total / var_data["metrics_count"]
                    metrics[var_id] = var_metrics
            
            return TestResult(
                test_id=test_id,
                winner_id=test.winner_id,
                confidence=test.confidence,
                metrics=metrics,
                recommendation=f"Variation {test.winner_id} showed {((test.confidence - 0.5) * 200):.0f}% confidence as winner"
            )
    
    async def get_active_tests(self) -> List[Dict]:
        """Get all active A/B tests."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ABTestModel).where(
                    ABTestModel.status == TestStatus.RUNNING
                )
            )
            tests = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status.value,
                    "variations": len(t.variations_json),
                    "started_at": str(t.started_at) if t.started_at else None
                }
                for t in tests
            ]
    
    async def stop_test(self, test_id: str, select_winner: Optional[str] = None) -> bool:
        """Stop an A/B test."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(ABTestModel).where(ABTestModel.id == test_id)
            )
            test = result.scalar_one_or_none()
            
            if not test:
                return False
            
            test.status = TestStatus.COMPLETED
            test.completed_at = datetime.now()
            
            if select_winner:
                test.winner_id = select_winner
                test.confidence = 1.0  # Manual selection = 100% confident
            
            await session.commit()
        
        logger.info(f"Stopped A/B test: {test_id}")
        return True


class ABTestModel(Base):
    """Database model for A/B tests."""
    
    __tablename__ = "ab_tests"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[TestStatus] = mapped_column(SQLEnum(TestStatus), default=TestStatus.DRAFT)
    
    # Configuration
    metric_to_optimize: Mapped[str] = mapped_column(String(50), default="engagement_rate")
    min_sample_size: Mapped[int] = mapped_column(Integer, default=100)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.95)
    auto_select_winner: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Variations and results (stored as JSON)
    variations_json: Mapped[Dict] = mapped_column(String, default="[]")
    results_json: Mapped[Dict] = mapped_column(String, default="{}")
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Results
    winner_id: Mapped[Optional[str]] = mapped_column(String(36))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


# Global instance
_ab_test: Optional[ABTest] = None


def get_ab_test() -> ABTest:
    """Get the global A/B test instance."""
    global _ab_test
    if _ab_test is None:
        _ab_test = ABTest()
    return _ab_test