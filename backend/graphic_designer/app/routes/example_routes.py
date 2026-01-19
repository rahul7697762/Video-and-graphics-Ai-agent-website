"""
Example Upload Routes - Learn from user-uploaded design examples
"""
import os
import base64
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List
from datetime import datetime
import uuid

from ..models.schemas import (
    ExampleUploadRequest, ExampleUploadResponse, DatasetSample, 
    DesignCopy, LayoutConfig
)
from ..models.database import get_dataset_db
from ..evaluators import get_evaluator
from ..storage import get_storage
from ..tenant import get_current_tenant, Tenant

router = APIRouter(prefix="/examples", tags=["Examples"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


@router.post("/upload", response_model=ExampleUploadResponse)
async def upload_example(
    file: UploadFile = File(...),
    brand_info: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
    labels: Optional[str] = Form(None),  # Comma-separated
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Upload an example design for the AI to learn from.
    
    The system will:
    1. Save the uploaded image
    2. Extract design features using AI
    3. Create a training sample entry
    """
    
    # Read file
    contents = await file.read()
    image_base64 = base64.b64encode(contents).decode('utf-8')
    
    # Generate ID
    example_id = str(uuid.uuid4())
    tenant_id = tenant.id if tenant else None
    
    # Save image
    storage = get_storage()
    image_path = await storage.save_image(
        image_base64,
        image_id=example_id,
        tenant_id=tenant_id,
        subfolder="examples"
    )
    
    # Extract features using AI
    extracted_features = {}
    if GEMINI_API_KEY:
        evaluator = get_evaluator(GEMINI_API_KEY)
        context = f"{brand_info or ''} {category or ''} {style or ''}"
        extracted_features = await evaluator.extract_features_from_example(
            image_base64,
            additional_context=context if context.strip() else None
        )
    
    # Parse labels
    label_list = [l.strip() for l in (labels or "").split(",") if l.strip()]
    
    # Determine final category/style from extraction or user input
    final_category = category or extracted_features.get('category', 'ready-to-move')
    final_style = style or extracted_features.get('style', 'modern')
    
    # Create layout config from extracted features
    layout_data = extracted_features.get('layout', {})
    layout_config = LayoutConfig(
        title_position=layout_data.get('title_position', 'top-center'),
        price_position=layout_data.get('price_position', 'bottom-right'),
        logo_position=layout_data.get('logo_position', 'bottom-left')
    )
    
    # Apply color theme if extracted
    colors = extracted_features.get('colors', {})
    if colors:
        layout_config.headline_color = colors.get('text_color', '#ffffff')
        layout_config.accent_color = colors.get('accent', '#ffffff')
    
    # Create dataset sample
    sample = DatasetSample(
        id=example_id,
        timestamp=datetime.utcnow(),
        raw_input=f"User example: {brand_info or file.filename}",
        visual_prompt=extracted_features.get('training_prompt', 'Professional real estate marketing design'),
        category=final_category,
        platform=extracted_features.get('platform_guess', 'Instagram Story'),
        style=final_style,
        color_theme=None,
        layout_config=layout_config,
        copy=DesignCopy(
            headline="[Example]",
            subtext="[User uploaded example]",
            cta="[Example]",
            keywords=label_list or extracted_features.get('effective_elements', [])
        ),
        image_path=image_path,
        tenant_id=tenant_id,
        selected_for_training=True  # User examples are pre-selected
    )
    
    # Save to dataset
    db = get_dataset_db()
    db.save_sample(sample)
    
    return ExampleUploadResponse(
        id=example_id,
        filename=file.filename,
        status="processed",
        extracted_features=extracted_features
    )


@router.post("/upload-batch")
async def upload_batch_examples(
    files: List[UploadFile] = File(...),
    brand_info: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Upload multiple example files at once."""
    
    results = []
    
    for file in files:
        try:
            # Process each file
            contents = await file.read()
            image_base64 = base64.b64encode(contents).decode('utf-8')
            
            example_id = str(uuid.uuid4())
            tenant_id = tenant.id if tenant else None
            
            # Save
            storage = get_storage()
            image_path = await storage.save_image(
                image_base64,
                image_id=example_id,
                tenant_id=tenant_id,
                subfolder="examples"
            )
            
            # Quick extraction (skip full analysis for batch)
            sample = DatasetSample(
                id=example_id,
                timestamp=datetime.utcnow(),
                raw_input=f"Batch example: {brand_info or file.filename}",
                visual_prompt="Professional real estate marketing design example",
                category=category or "ready-to-move",
                platform="Instagram Story",
                style=style or "modern",
                color_theme=None,
                layout_config=LayoutConfig(),
                copy=DesignCopy(
                    headline="[Batch Example]",
                    subtext="[User uploaded]",
                    cta="[Example]",
                    keywords=[]
                ),
                image_path=image_path,
                tenant_id=tenant_id,
                selected_for_training=True
            )
            
            db = get_dataset_db()
            db.save_sample(sample)
            
            results.append({
                "id": example_id,
                "filename": file.filename,
                "status": "success"
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "processed": len([r for r in results if r.get('status') == 'success']),
        "failed": len([r for r in results if r.get('status') == 'failed']),
        "results": results
    }


@router.get("/")
async def list_examples(
    limit: int = 50,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """List uploaded examples."""
    
    db = get_dataset_db()
    tenant_id = tenant.id if tenant else None
    
    samples = db.get_all_samples(tenant_id=tenant_id, limit=limit)
    
    # Filter to examples only (those with [Example] in headline)
    examples = [s for s in samples if '[Example]' in s.copy.headline or '[Batch Example]' in s.copy.headline]
    
    return {
        "count": len(examples),
        "examples": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if hasattr(s.timestamp, 'isoformat') else str(s.timestamp),
                "category": s.category,
                "style": s.style,
                "image_path": s.image_path
            }
            for s in examples
        ]
    }


@router.delete("/{example_id}")
async def delete_example(
    example_id: str,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Delete an uploaded example."""
    
    db = get_dataset_db()
    sample = db.get_sample(example_id)
    
    if not sample:
        raise HTTPException(status_code=404, detail="Example not found")
    
    if tenant and sample.tenant_id and sample.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete image
    storage = get_storage()
    await storage.delete_image(sample.image_path)
    
    # Mark as deleted (soft delete via update)
    db.update_sample(example_id, {
        "selected_for_training": False,
        "feedback": {"feedback_type": "deleted"}
    })
    
    return {"message": "Example deleted", "id": example_id}
