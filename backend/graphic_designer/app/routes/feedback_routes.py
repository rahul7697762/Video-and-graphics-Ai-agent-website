"""
Feedback Routes - Handle user feedback on designs
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime

from ..models.schemas import (
    FeedbackRequest, FeedbackResponse, DatasetSample
)
from ..models.database import get_dataset_db
from ..tenant import get_current_tenant, Tenant

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Submit feedback for a generated design.
    
    Feedback types:
    - approve: Mark as good quality for training
    - reject: Mark as poor quality  
    - edit: Provide corrections
    """
    
    db = get_dataset_db()
    sample = db.get_sample(request.design_id)
    
    if not sample:
        raise HTTPException(status_code=404, detail="Design not found")
    
    # Check tenant ownership
    if tenant and sample.tenant_id and sample.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Build feedback data
    feedback_data = {
        "feedback_type": request.feedback_type.value,
        "rating": request.rating,
        "comments": request.comments,
        "corrections": request.corrections,
        "submitted_at": datetime.utcnow().isoformat(),
        "submitted_by": tenant.id if tenant else "anonymous"
    }
    
    # Update sample with feedback
    success = db.update_sample(request.design_id, {"feedback": feedback_data})
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    
    # Auto-select for training if approved with high rating
    if request.feedback_type.value == "approve" and request.rating and request.rating >= 4:
        db.update_sample(request.design_id, {"selected_for_training": True})
    
    return FeedbackResponse(
        id=f"fb_{request.design_id}",
        design_id=request.design_id,
        status="saved",
        message=f"Feedback '{request.feedback_type.value}' recorded successfully"
    )


@router.get("/{design_id}")
async def get_feedback(
    design_id: str,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Get feedback for a specific design."""
    
    db = get_dataset_db()
    sample = db.get_sample(design_id)
    
    if not sample:
        raise HTTPException(status_code=404, detail="Design not found")
    
    if tenant and sample.tenant_id and sample.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "design_id": design_id,
        "feedback": sample.feedback,
        "evaluation_scores": sample.evaluation_scores.model_dump() if sample.evaluation_scores else None,
        "selected_for_training": sample.selected_for_training
    }


@router.post("/{design_id}/select-for-training")
async def select_for_training(
    design_id: str,
    selected: bool = True,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Manually select/deselect a design for training."""
    
    db = get_dataset_db()
    sample = db.get_sample(design_id)
    
    if not sample:
        raise HTTPException(status_code=404, detail="Design not found")
    
    if tenant and sample.tenant_id and sample.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.update_sample(design_id, {"selected_for_training": selected})
    
    return {
        "design_id": design_id,
        "selected_for_training": selected,
        "message": "Training selection updated"
    }


@router.get("/stats/summary")
async def get_feedback_stats(tenant: Optional[Tenant] = Depends(get_current_tenant)):
    """Get feedback statistics."""
    
    db = get_dataset_db()
    tenant_id = tenant.id if tenant else None
    
    stats = db.get_stats(tenant_id)
    
    return {
        "total_designs": stats.get('total_samples', 0),
        "approved": stats.get('approved_samples', 0),
        "rejected": stats.get('rejected_samples', 0),
        "pending_review": stats.get('pending_samples', 0),
        "average_score": stats.get('avg_score', 0),
        "approval_rate": round(
            stats.get('approved_samples', 0) / max(stats.get('total_samples', 1), 1) * 100, 1
        )
    }
