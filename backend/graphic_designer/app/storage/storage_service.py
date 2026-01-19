"""
GCS Storage Service for image and dataset management
"""
import os
import asyncio
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, BinaryIO
import uuid

from google.cloud import storage


class StorageService:
    """Handles file storage for images and datasets."""
    
    def __init__(self, 
                 project_id: Optional[str] = None,
                 gcs_bucket: Optional[str] = None,
                 local_fallback: bool = True):
        self.project_id = project_id
        self.gcs_bucket = gcs_bucket
        self.local_fallback = local_fallback
        self.use_gcs = bool(gcs_bucket and project_id)
        
        if self.use_gcs:
            try:
                self.storage_client = storage.Client(project=project_id)
                self.bucket = self.storage_client.bucket(gcs_bucket)
            except Exception as e:
                print(f"GCS init failed, using local storage: {e}")
                self.use_gcs = False
        
        # Local storage paths
        self.local_base = Path(__file__).parent.parent.parent
        self.local_images = self.local_base / "dataset" / "images"
        self.local_images.mkdir(parents=True, exist_ok=True)
    
    async def save_image(self,
                         image_base64: str,
                         image_id: Optional[str] = None,
                         tenant_id: Optional[str] = None,
                         subfolder: str = "generated") -> str:
        """Save a base64 image and return the path/URL."""
        
        image_id = image_id or str(uuid.uuid4())
        filename = f"{image_id}.png"
        
        # Decode image
        image_data = base64.b64decode(image_base64)
        
        if self.use_gcs:
            return await self._save_to_gcs(image_data, filename, tenant_id, subfolder)
        else:
            return await self._save_locally(image_data, filename, tenant_id, subfolder)
    
    async def _save_to_gcs(self,
                           data: bytes,
                           filename: str,
                           tenant_id: Optional[str],
                           subfolder: str) -> str:
        """Save to Google Cloud Storage."""
        
        path = f"images/{tenant_id or 'global'}/{subfolder}/{filename}"
        blob = self.bucket.blob(path)
        
        await asyncio.to_thread(blob.upload_from_string, data, content_type="image/png")
        
        # Make publicly accessible or return signed URL
        # For now, return the GCS path
        return f"gs://{self.gcs_bucket}/{path}"
    
    async def _save_locally(self,
                            data: bytes,
                            filename: str,
                            tenant_id: Optional[str],
                            subfolder: str) -> str:
        """Save to local filesystem."""
        
        target_dir = self.local_images
        if tenant_id:
            target_dir = target_dir / tenant_id
        target_dir = target_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = target_dir / filename
        
        await asyncio.to_thread(self._write_file, filepath, data)
        
        return str(filepath)
    
    def _write_file(self, filepath: Path, data: bytes):
        with open(filepath, 'wb') as f:
            f.write(data)
    
    async def load_image(self, path: str) -> Optional[str]:
        """Load an image and return as base64."""
        
        if path.startswith("gs://"):
            return await self._load_from_gcs(path)
        else:
            return await self._load_locally(path)
    
    async def _load_from_gcs(self, gcs_path: str) -> Optional[str]:
        """Load from GCS."""
        
        try:
            # Parse gs://bucket/path
            parts = gcs_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            data = await asyncio.to_thread(blob.download_as_bytes)
            return base64.b64encode(data).decode('utf-8')
        except Exception as e:
            print(f"Failed to load from GCS: {e}")
            return None
    
    async def _load_locally(self, filepath: str) -> Optional[str]:
        """Load from local filesystem."""
        
        try:
            path = Path(filepath)
            if not path.exists():
                return None
            
            with open(path, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode('utf-8')
        except Exception as e:
            print(f"Failed to load locally: {e}")
            return None
    
    async def delete_image(self, path: str) -> bool:
        """Delete an image."""
        
        if path.startswith("gs://"):
            return await self._delete_from_gcs(path)
        else:
            return await self._delete_locally(path)
    
    async def _delete_from_gcs(self, gcs_path: str) -> bool:
        try:
            parts = gcs_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            await asyncio.to_thread(blob.delete)
            return True
        except:
            return False
    
    async def _delete_locally(self, filepath: str) -> bool:
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
            return True
        except:
            return False
    
    async def upload_example(self,
                             file_data: bytes,
                             filename: str,
                             tenant_id: Optional[str] = None) -> str:
        """Upload a user example image."""
        
        example_id = str(uuid.uuid4())
        ext = Path(filename).suffix or ".png"
        new_filename = f"{example_id}{ext}"
        
        if self.use_gcs:
            path = f"examples/{tenant_id or 'global'}/{new_filename}"
            blob = self.bucket.blob(path)
            await asyncio.to_thread(blob.upload_from_string, file_data)
            return f"gs://{self.gcs_bucket}/{path}"
        else:
            examples_dir = self.local_base / "dataset" / "examples"
            if tenant_id:
                examples_dir = examples_dir / tenant_id
            examples_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = examples_dir / new_filename
            await asyncio.to_thread(self._write_file, filepath, file_data)
            return str(filepath)
    
    def get_local_image_path(self, image_id: str) -> Path:
        """Get local path for an image by ID."""
        return self.local_images / f"{image_id}.png"
    
    async def list_images(self, 
                          tenant_id: Optional[str] = None,
                          subfolder: str = "generated",
                          limit: int = 100) -> list:
        """List stored images."""
        
        if self.use_gcs:
            prefix = f"images/{tenant_id or 'global'}/{subfolder}/"
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=limit)
            return [f"gs://{self.gcs_bucket}/{b.name}" for b in blobs]
        else:
            target_dir = self.local_images
            if tenant_id:
                target_dir = target_dir / tenant_id
            target_dir = target_dir / subfolder
            
            if not target_dir.exists():
                return []
            
            return [str(p) for p in list(target_dir.glob("*.png"))[:limit]]


# Singleton
_storage: Optional[StorageService] = None

def get_storage(project_id: Optional[str] = None, 
                gcs_bucket: Optional[str] = None) -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService(project_id, gcs_bucket)
    return _storage
