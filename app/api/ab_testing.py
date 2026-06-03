"""
A/B Testing API endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.core.ab_testing import get_ab_test, Variation


router = APIRouter()


class CreateTestRequest(BaseModel):
    name: str
    description: str = ""
    variations: List[Dict[str, Any]]
    metric_to_optimize: str = "engagement_rate"
    min_sample_size: int = 100
    confidence_threshold: float = 0.95
    auto_select_winner: bool = True


class RecordResultRequest(BaseModel):
    variation_id: str
    metrics: Dict[str, float]


@router.post("/tests")
async def create_test(request: CreateTestRequest) -> Dict:
    """Create a new A/B test."""
    ab_test = get_ab_test()
    
    variations = [
        Variation(
            id=v.get("id", str(i)),
            name=v.get("name", f"Variation {i}"),
            content_params=v.get("content_params", {}),
            is_control=v.get("is_control", i == 0)
        )
        for i, v in enumerate(request.variations)
    ]
    
    test_id = await ab_test.create_test(
        name=request.name,
        description=request.description,
        variations=variations,
        metric_to_optimize=request.metric_to_optimize,
        min_sample_size=request.min_sample_size,
        confidence_threshold=request.confidence_threshold,
        auto_select_winner=request.auto_select_winner
    )
    
    return {
        "success": True,
        "test_id": test_id,
        "message": f"Created A/B test '{request.name}' with {len(variations)} variations"
    }


@router.get("/tests")
async def list_tests() -> Dict:
    """List all A/B tests."""
    ab_test = get_ab_test()
    tests = await ab_test.get_active_tests()
    
    return {"tests": tests}


@router.post("/tests/{test_id}/start")
async def start_test(test_id: str) -> Dict:
    """Start an A/B test."""
    ab_test = get_ab_test()
    success = await ab_test.start_test(test_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {"success": True, "message": f"Started test {test_id}"}


@router.get("/tests/{test_id}/variation")
async def get_next_variation(test_id: str) -> Dict:
    """Get next variation to show."""
    ab_test = get_ab_test()
    variation = await ab_test.get_next_variation(test_id)
    
    if not variation:
        raise HTTPException(status_code=404, detail="Test not found or not running")
    
    return {
        "variation": {
            "id": variation.id,
            "name": variation.name,
            "content_params": variation.content_params,
            "is_control": variation.is_control
        }
    }


@router.post("/tests/{test_id}/result")
async def record_result(test_id: str, request: RecordResultRequest) -> Dict:
    """Record result for a variation."""
    ab_test = get_ab_test()
    success = await ab_test.record_result(
        test_id=test_id,
        variation_id=request.variation_id,
        metrics=request.metrics
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {"success": True, "message": "Result recorded"}


@router.get("/tests/{test_id}/results")
async def get_test_results(test_id: str) -> Dict:
    """Get test results."""
    ab_test = get_ab_test()
    results = await ab_test.get_test_results(test_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="Test not found or not completed")
    
    return {
        "test_id": results.test_id,
        "winner_id": results.winner_id,
        "confidence": results.confidence,
        "metrics": results.metrics,
        "recommendation": results.recommendation
    }


@router.post("/tests/{test_id}/stop")
async def stop_test(test_id: str, winner_id: Optional[str] = None) -> Dict:
    """Stop an A/B test."""
    ab_test = get_ab_test()
    success = await ab_test.stop_test(test_id, winner_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {
        "success": True,
        "message": f"Stopped test {test_id}",
        "winner_id": winner_id
    }