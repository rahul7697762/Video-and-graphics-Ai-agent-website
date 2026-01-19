"""
Training Routes - Handle model training and management
"""
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, List
from datetime import datetime

from ..models.schemas import (
    TrainingRequest, TrainingJob, TrainingStatus, ModelInfo, DatasetStats
)
from ..models.database import get_dataset_db, get_model_registry
from ..trainers import get_trainer
from ..datasets import get_selector
from ..tenant import get_current_tenant, require_tenant, Tenant

router = APIRouter(prefix="/training", tags=["Training"])

# Config from environment
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET = os.getenv("GCS_TRAINING_BUCKET", "")


@router.post("/train-model", response_model=TrainingJob)
async def start_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Start a new model training job.
    
    This will:
    1. Select training samples using active learning
    2. Prepare and upload dataset to GCS
    3. Start Vertex AI fine-tuning job
    """
    
    if not PROJECT_ID or not GCS_BUCKET:
        raise HTTPException(
            status_code=500, 
            detail="Training not configured. Set GOOGLE_CLOUD_PROJECT and GCS_TRAINING_BUCKET."
        )
    
    tenant_id = tenant.id if tenant else request.tenant_id
    
    # Select samples for training
    selector = get_selector()
    samples = selector.select_for_training(
        target_count=500,
        tenant_id=tenant_id,
        include_approved=True,
        include_low_scores=True
    )
    
    if len(samples) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough training data. Found {len(samples)} samples, need at least 10."
        )
    
    # Get trainer
    trainer = get_trainer(PROJECT_ID, LOCATION, GCS_BUCKET)
    
    # Prepare dataset
    try:
        dataset_path = await trainer.prepare_training_dataset(
            samples, 
            request.model_type,
            tenant_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset preparation failed: {str(e)}")
    
    # Start training job (async)
    job = await trainer.start_training_job(
        model_type=request.model_type,
        dataset_gcs_path=dataset_path,
        epochs=request.epochs,
        learning_rate=request.learning_rate,
        tenant_id=tenant_id
    )
    
    return job


@router.get("/training-status/{job_id}", response_model=TrainingJob)
async def get_training_status(job_id: str):
    """Get the status of a training job."""
    
    if not PROJECT_ID:
        raise HTTPException(status_code=500, detail="Training not configured")
    
    trainer = get_trainer(PROJECT_ID, LOCATION, GCS_BUCKET)
    job = await trainer.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    return job


@router.get("/jobs", response_model=List[TrainingJob])
async def list_training_jobs(
    limit: int = 10,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """List recent training jobs."""
    
    registry = get_model_registry()
    jobs = registry.get_recent_jobs(limit)
    
    return jobs


@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    model_type: Optional[str] = None,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """List all registered models."""
    
    registry = get_model_registry()
    models = registry.get_all_models(model_type)
    
    return models


@router.get("/models/active/{model_type}", response_model=ModelInfo)
async def get_active_model(model_type: str):
    """Get the currently active model for a type."""
    
    registry = get_model_registry()
    model = registry.get_active_model(model_type)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"No active {model_type} model found")
    
    return model


@router.post("/models/{model_id}/activate")
async def activate_model(
    model_id: str,
    tenant: Tenant = Depends(require_tenant)
):
    """Set a model as the active model for inference."""
    
    registry = get_model_registry()
    models = registry.get_all_models()
    
    target_model = None
    for model in models:
        if model.id == model_id:
            target_model = model
            break
    
    if not target_model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    success = registry.set_active_model(target_model.type, model_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to activate model")
    
    return {"message": f"Model {model_id} is now active", "model_type": target_model.type}


@router.post("/models/{model_type}/rollback")
async def rollback_model(
    model_type: str,
    version: int = 1,
    tenant: Tenant = Depends(require_tenant)
):
    """Rollback to a previous model version."""
    
    registry = get_model_registry()
    model = registry.rollback_model(model_type, version)
    
    if not model:
        raise HTTPException(status_code=400, detail=f"Cannot rollback {version} versions")
    
    return {
        "message": f"Rolled back to {model.name}",
        "model_id": model.id,
        "version": model.version
    }


@router.get("/dataset/stats", response_model=DatasetStats)
async def get_dataset_stats(tenant: Optional[Tenant] = Depends(get_current_tenant)):
    """Get dataset statistics."""
    
    db = get_dataset_db()
    tenant_id = tenant.id if tenant else None
    
    stats = db.get_stats(tenant_id)
    
    return DatasetStats(**stats)


@router.get("/dataset/balance")
async def get_dataset_balance(tenant: Optional[Tenant] = Depends(get_current_tenant)):
    """Get dataset balance analysis with recommendations."""
    
    selector = get_selector()
    tenant_id = tenant.id if tenant else None
    
    return selector.calculate_dataset_balance_score(tenant_id)


@router.get("/dataset/underrepresented")
async def get_underrepresented(tenant: Optional[Tenant] = Depends(get_current_tenant)):
    """Get underrepresented categories for targeted data collection."""
    
    selector = get_selector()
    tenant_id = tenant.id if tenant else None
    
    return selector.get_underrepresented_categories(tenant_id=tenant_id)


@router.post("/dataset/export")
async def export_dataset(
    format: str = "jsonl",
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Export dataset for external training."""
    
    if not PROJECT_ID:
        raise HTTPException(status_code=500, detail="Training not configured")
    
    selector = get_selector()
    tenant_id = tenant.id if tenant else None
    
    samples = selector.select_for_training(target_count=1000, tenant_id=tenant_id)
    
    trainer = get_trainer(PROJECT_ID, LOCATION, GCS_BUCKET)
    export_path = await trainer.export_dataset_for_external_training(samples, format)
    
    return {
        "export_path": export_path,
        "sample_count": len(samples),
        "format": format
    }
