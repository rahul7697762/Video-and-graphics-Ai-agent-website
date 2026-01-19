"""
LoRA Fine-Tuning Trainer for Vertex AI Imagen/Gemini Models
"""
import os
import json
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from google.cloud import aiplatform
from google.cloud import storage

from ..models.schemas import (
    TrainingJob, TrainingStatus, ModelInfo, DatasetSample
)
from ..models.database import get_dataset_db, get_model_registry


class LoRATrainer:
    """Handles LoRA fine-tuning for Imagen and Gemini models on Vertex AI."""
    
    def __init__(self, project_id: str, location: str, gcs_bucket: str):
        self.project_id = project_id
        self.location = location
        self.gcs_bucket = gcs_bucket
        self.storage_client = storage.Client(project=project_id)
        
        aiplatform.init(project=project_id, location=location)
    
    async def prepare_training_dataset(self,
                                        samples: List[DatasetSample],
                                        model_type: str,
                                        tenant_id: Optional[str] = None) -> str:
        """
        Prepare and upload training dataset to GCS.
        Returns GCS path to the dataset.
        """
        
        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"training_{model_type}_{timestamp}_{job_id}"
        
        # Create local temp directory
        local_dir = Path(__file__).parent.parent.parent / "temp" / dataset_name
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare dataset based on model type
        if model_type == "imagen":
            manifest = await self._prepare_imagen_dataset(samples, local_dir)
        else:  # gemini
            manifest = await self._prepare_gemini_dataset(samples, local_dir)
        
        # Upload to GCS
        gcs_path = await self._upload_to_gcs(local_dir, dataset_name, tenant_id)
        
        return gcs_path
    
    async def _prepare_imagen_dataset(self, 
                                       samples: List[DatasetSample],
                                       local_dir: Path) -> Dict[str, Any]:
        """Prepare Imagen training data (prompt + image pairs)."""
        
        images_dir = local_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        manifest = []
        dataset_db = get_dataset_db()
        
        for i, sample in enumerate(samples):
            # Copy/reference image
            source_path = dataset_db.images_dir / f"{sample.id}.png"
            if source_path.exists():
                target_path = images_dir / f"img_{i:05d}.png"
                import shutil
                shutil.copy(source_path, target_path)
                
                manifest.append({
                    "image": f"images/img_{i:05d}.png",
                    "prompt": sample.visual_prompt,
                    "category": sample.category,
                    "style": sample.style
                })
        
        # Write manifest
        with open(local_dir / "manifest.jsonl", 'w') as f:
            for entry in manifest:
                f.write(json.dumps(entry) + '\n')
        
        return {"count": len(manifest), "type": "imagen"}
    
    async def _prepare_gemini_dataset(self,
                                       samples: List[DatasetSample],
                                       local_dir: Path) -> Dict[str, Any]:
        """Prepare Gemini training data (input/output pairs for tuning)."""
        
        training_data = []
        
        for sample in samples:
            # Create input/output pairs for Gemini tuning
            input_text = f"""
            Generate a design plan for:
            Category: {sample.category}
            Platform: {sample.platform}
            Style: {sample.style}
            Details: {sample.raw_input}
            """
            
            output_text = json.dumps({
                "visual_prompt": sample.visual_prompt,
                "copy": sample.copy.model_dump() if hasattr(sample.copy, 'model_dump') else sample.copy,
                "layout": sample.layout_config.model_dump() if hasattr(sample.layout_config, 'model_dump') else sample.layout_config
            })
            
            training_data.append({
                "input": input_text.strip(),
                "output": output_text
            })
        
        # Write training data
        with open(local_dir / "training_data.jsonl", 'w') as f:
            for entry in training_data:
                f.write(json.dumps(entry) + '\n')
        
        return {"count": len(training_data), "type": "gemini"}
    
    async def _upload_to_gcs(self, 
                              local_dir: Path,
                              dataset_name: str,
                              tenant_id: Optional[str] = None) -> str:
        """Upload dataset directory to GCS."""
        
        bucket = self.storage_client.bucket(self.gcs_bucket)
        prefix = f"training_datasets/{tenant_id or 'global'}/{dataset_name}"
        
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                blob_name = f"{prefix}/{relative_path}"
                blob = bucket.blob(blob_name)
                
                await asyncio.to_thread(
                    blob.upload_from_filename,
                    str(file_path)
                )
        
        return f"gs://{self.gcs_bucket}/{prefix}"
    
    async def start_training_job(self,
                                  model_type: str,
                                  dataset_gcs_path: str,
                                  epochs: int = 100,
                                  learning_rate: float = 1e-4,
                                  tenant_id: Optional[str] = None) -> TrainingJob:
        """Start a Vertex AI fine-tuning job."""
        
        job_id = str(uuid.uuid4())
        
        job = TrainingJob(
            id=job_id,
            status=TrainingStatus.PREPARING,
            model_type=model_type,
            started_at=datetime.utcnow()
        )
        
        # Save job to registry
        registry = get_model_registry()
        registry.save_training_job(job)
        
        try:
            if model_type == "imagen":
                await self._start_imagen_tuning(job_id, dataset_gcs_path, epochs, learning_rate)
            else:
                await self._start_gemini_tuning(job_id, dataset_gcs_path, epochs, learning_rate)
            
            # Update status
            registry.update_training_job(job_id, {"status": TrainingStatus.TRAINING.value})
            job.status = TrainingStatus.TRAINING
            
        except Exception as e:
            registry.update_training_job(job_id, {
                "status": TrainingStatus.FAILED.value,
                "error": str(e)
            })
            job.status = TrainingStatus.FAILED
            job.error = str(e)
        
        return job
    
    async def _start_imagen_tuning(self,
                                    job_id: str,
                                    dataset_path: str,
                                    epochs: int,
                                    learning_rate: float):
        """Start Imagen LoRA tuning on Vertex AI."""
        
        # Note: Actual Imagen tuning API may vary
        # This is a placeholder for the Vertex AI tuning job
        
        training_job = aiplatform.CustomTrainingJob(
            display_name=f"imagen_lora_{job_id}",
            script_path="train_imagen_lora.py",  # Would need actual script
            container_uri="gcr.io/cloud-aiplatform/training/pytorch-gpu.1-13:latest",
            requirements=["torch", "diffusers", "peft"],
            model_serving_container_image_uri="gcr.io/cloud-aiplatform/prediction/pytorch-gpu.1-13:latest"
        )
        
        # In reality, you'd launch this as an async background task
        # For now, we log the intent
        print(f"Would start Imagen LoRA training job: {job_id}")
        print(f"Dataset: {dataset_path}")
        print(f"Epochs: {epochs}, LR: {learning_rate}")
    
    async def _start_gemini_tuning(self,
                                    job_id: str,
                                    dataset_path: str,
                                    epochs: int,
                                    learning_rate: float):
        """Start Gemini tuning on Vertex AI."""
        
        # Gemini tuning via Vertex AI Generative AI API
        # Reference: https://cloud.google.com/vertex-ai/docs/generative-ai/models/tune-models
        
        print(f"Would start Gemini tuning job: {job_id}")
        print(f"Dataset: {dataset_path}")
        print(f"Epochs: {epochs}, LR: {learning_rate}")
        
        # Actual implementation would use:
        # from vertexai.preview.language_models import TextGenerationModel
        # model = TextGenerationModel.from_pretrained("text-bison@001")
        # tuning_job = model.tune_model(...)
    
    async def get_job_status(self, job_id: str) -> Optional[TrainingJob]:
        """Get current status of a training job."""
        
        registry = get_model_registry()
        return registry.get_training_job(job_id)
    
    async def register_completed_model(self,
                                        job_id: str,
                                        model_path: str,
                                        metrics: Dict[str, float]) -> ModelInfo:
        """Register a completed fine-tuned model."""
        
        job = await self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        model = ModelInfo(
            id=str(uuid.uuid4()),
            name=f"{job.model_type}_lora_{job_id[:8]}",
            type=job.model_type,
            version=datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            created_at=datetime.utcnow(),
            is_active=False,
            metrics=metrics,
            gcs_path=model_path
        )
        
        registry = get_model_registry()
        registry.register_model(model)
        
        # Update job as completed
        registry.update_training_job(job_id, {
            "status": TrainingStatus.COMPLETED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "model_path": model_path,
            "metrics": metrics
        })
        
        return model
    
    async def export_dataset_for_external_training(self,
                                                    samples: List[DatasetSample],
                                                    format: str = "jsonl") -> str:
        """Export dataset for external training tools."""
        
        export_dir = Path(__file__).parent.parent.parent / "exports"
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"dataset_export_{timestamp}.{format}"
        
        with open(export_file, 'w') as f:
            for sample in samples:
                record = {
                    "id": sample.id,
                    "prompt": sample.visual_prompt,
                    "raw_input": sample.raw_input,
                    "category": sample.category,
                    "platform": sample.platform,
                    "style": sample.style,
                    "image_path": sample.image_path,
                    "scores": sample.evaluation_scores.model_dump() if sample.evaluation_scores else None
                }
                f.write(json.dumps(record) + '\n')
        
        return str(export_file)


# Create trainer instance
_trainer: Optional[LoRATrainer] = None

def get_trainer(project_id: str, location: str, gcs_bucket: str) -> LoRATrainer:
    global _trainer
    if _trainer is None:
        _trainer = LoRATrainer(project_id, location, gcs_bucket)
    return _trainer
