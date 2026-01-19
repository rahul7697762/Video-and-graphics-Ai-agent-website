"""
Database Layer - Using JSON files for simplicity (can be swapped to PostgreSQL/Supabase)
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import threading
from filelock import FileLock

from .schemas import (
    DatasetSample, Tenant, BrandKit, TrainingJob, ModelInfo,
    FeedbackRequest, EvaluationScores
)


class JSONDatabase:
    """Thread-safe JSON file database for rapid prototyping."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, FileLock] = {}
        self._lock = threading.Lock()
    
    def _get_file_lock(self, filename: str) -> FileLock:
        with self._lock:
            if filename not in self._locks:
                lock_path = self.base_path / f"{filename}.lock"
                self._locks[filename] = FileLock(str(lock_path))
            return self._locks[filename]
    
    def _read_jsonl(self, filename: str) -> List[Dict[str, Any]]:
        filepath = self.base_path / filename
        if not filepath.exists():
            return []
        
        with self._get_file_lock(filename):
            records = []
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return records
    
    def _append_jsonl(self, filename: str, record: Dict[str, Any]):
        filepath = self.base_path / filename
        with self._get_file_lock(filename):
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, default=str) + '\n')
    
    def _write_jsonl(self, filename: str, records: List[Dict[str, Any]]):
        filepath = self.base_path / filename
        with self._get_file_lock(filename):
            with open(filepath, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, default=str) + '\n')
    
    def _read_json(self, filename: str) -> Dict[str, Any]:
        filepath = self.base_path / filename
        if not filepath.exists():
            return {}
        with self._get_file_lock(filename):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _write_json(self, filename: str, data: Dict[str, Any]):
        filepath = self.base_path / filename
        with self._get_file_lock(filename):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)


class DatasetDB(JSONDatabase):
    """Dataset storage and retrieval."""
    
    def __init__(self, base_path: Path):
        super().__init__(base_path)
        self.metadata_file = "metadata.jsonl"
        self.images_dir = base_path / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def save_sample(self, sample: DatasetSample) -> str:
        record = sample.model_dump()
        self._append_jsonl(self.metadata_file, record)
        return sample.id
    
    def get_sample(self, sample_id: str) -> Optional[DatasetSample]:
        records = self._read_jsonl(self.metadata_file)
        for record in records:
            if record.get('id') == sample_id:
                return DatasetSample(**record)
        return None
    
    def get_all_samples(self, 
                        tenant_id: Optional[str] = None,
                        category: Optional[str] = None,
                        platform: Optional[str] = None,
                        style: Optional[str] = None,
                        limit: int = 1000) -> List[DatasetSample]:
        records = self._read_jsonl(self.metadata_file)
        samples = []
        
        for record in records[-limit:]:
            if tenant_id and record.get('tenant_id') != tenant_id:
                continue
            if category and record.get('category') != category:
                continue
            if platform and record.get('platform') != platform:
                continue
            if style and record.get('style') != style:
                continue
            try:
                samples.append(DatasetSample(**record))
            except:
                continue
        
        return samples
    
    def update_sample(self, sample_id: str, updates: Dict[str, Any]) -> bool:
        records = self._read_jsonl(self.metadata_file)
        updated = False
        
        for i, record in enumerate(records):
            if record.get('id') == sample_id:
                records[i].update(updates)
                updated = True
                break
        
        if updated:
            self._write_jsonl(self.metadata_file, records)
        
        return updated
    
    def get_training_candidates(self, 
                                 min_score: float = 0.0,
                                 max_score: float = 10.0,
                                 approved_only: bool = False,
                                 limit: int = 500) -> List[DatasetSample]:
        records = self._read_jsonl(self.metadata_file)
        candidates = []
        
        for record in records:
            scores = record.get('evaluation_scores')
            feedback = record.get('feedback')
            
            if approved_only and (not feedback or feedback.get('feedback_type') != 'approve'):
                continue
            
            if scores:
                avg = (scores.get('photorealism', 5) + scores.get('layout_alignment', 5) +
                       scores.get('readability', 5) + scores.get('real_estate_relevance', 5) +
                       scores.get('overall_quality', 5)) / 5
                if min_score <= avg <= max_score:
                    try:
                        candidates.append(DatasetSample(**record))
                    except:
                        continue
        
        return candidates[:limit]
    
    def get_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        records = self._read_jsonl(self.metadata_file)
        
        if tenant_id:
            records = [r for r in records if r.get('tenant_id') == tenant_id]
        
        stats = {
            'total_samples': len(records),
            'approved_samples': 0,
            'rejected_samples': 0,
            'pending_samples': 0,
            'avg_score': 0.0,
            'category_distribution': {},
            'platform_distribution': {},
            'style_distribution': {}
        }
        
        score_sum = 0
        score_count = 0
        
        for record in records:
            # Feedback stats
            feedback = record.get('feedback')
            if feedback:
                ft = feedback.get('feedback_type')
                if ft == 'approve':
                    stats['approved_samples'] += 1
                elif ft == 'reject':
                    stats['rejected_samples'] += 1
            else:
                stats['pending_samples'] += 1
            
            # Score stats
            scores = record.get('evaluation_scores')
            if scores:
                avg = (scores.get('photorealism', 5) + scores.get('layout_alignment', 5) +
                       scores.get('readability', 5) + scores.get('real_estate_relevance', 5) +
                       scores.get('overall_quality', 5)) / 5
                score_sum += avg
                score_count += 1
            
            # Distribution stats
            cat = record.get('category', 'unknown')
            plat = record.get('platform', 'unknown')
            sty = record.get('style', 'unknown')
            
            stats['category_distribution'][cat] = stats['category_distribution'].get(cat, 0) + 1
            stats['platform_distribution'][plat] = stats['platform_distribution'].get(plat, 0) + 1
            stats['style_distribution'][sty] = stats['style_distribution'].get(sty, 0) + 1
        
        if score_count > 0:
            stats['avg_score'] = round(score_sum / score_count, 2)
        
        return stats


class TenantDB(JSONDatabase):
    """Tenant management."""
    
    def __init__(self, base_path: Path):
        super().__init__(base_path)
        self.tenants_file = "tenants.json"
        self.brand_kits_file = "brand_kits.json"
    
    def create_tenant(self, name: str, email: str) -> Tenant:
        tenants = self._read_json(self.tenants_file)
        
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            api_key=f"sk_{uuid.uuid4().hex[:32]}"
        )
        
        tenants[tenant.id] = tenant.model_dump()
        self._write_json(self.tenants_file, tenants)
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        tenants = self._read_json(self.tenants_file)
        data = tenants.get(tenant_id)
        return Tenant(**data) if data else None
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        tenants = self._read_json(self.tenants_file)
        for data in tenants.values():
            if data.get('api_key') == api_key:
                return Tenant(**data)
        return None
    
    def update_usage(self, tenant_id: str, increment: int = 1) -> bool:
        tenants = self._read_json(self.tenants_file)
        if tenant_id in tenants:
            tenants[tenant_id]['usage_count'] = tenants[tenant_id].get('usage_count', 0) + increment
            self._write_json(self.tenants_file, tenants)
            return True
        return False
    
    def create_brand_kit(self, brand_kit: BrandKit) -> str:
        kits = self._read_json(self.brand_kits_file)
        kits[brand_kit.id] = brand_kit.model_dump()
        self._write_json(self.brand_kits_file, kits)
        
        # Link to tenant
        tenants = self._read_json(self.tenants_file)
        if brand_kit.tenant_id in tenants:
            if 'brand_kits' not in tenants[brand_kit.tenant_id]:
                tenants[brand_kit.tenant_id]['brand_kits'] = []
            tenants[brand_kit.tenant_id]['brand_kits'].append(brand_kit.id)
            self._write_json(self.tenants_file, tenants)
        
        return brand_kit.id
    
    def get_brand_kit(self, kit_id: str) -> Optional[BrandKit]:
        kits = self._read_json(self.brand_kits_file)
        data = kits.get(kit_id)
        return BrandKit(**data) if data else None
    
    def get_tenant_brand_kits(self, tenant_id: str) -> List[BrandKit]:
        kits = self._read_json(self.brand_kits_file)
        return [BrandKit(**data) for data in kits.values() if data.get('tenant_id') == tenant_id]


class ModelRegistryDB(JSONDatabase):
    """Model version management."""
    
    def __init__(self, base_path: Path):
        super().__init__(base_path)
        self.registry_file = "model_registry.json"
        self.jobs_file = "training_jobs.jsonl"
    
    def register_model(self, model: ModelInfo) -> str:
        registry = self._read_json(self.registry_file)
        
        if 'models' not in registry:
            registry['models'] = {}
        if 'active' not in registry:
            registry['active'] = {}
        
        registry['models'][model.id] = model.model_dump()
        
        # Set as active if first of type
        if model.type not in registry['active']:
            registry['active'][model.type] = model.id
        
        self._write_json(self.registry_file, registry)
        return model.id
    
    def set_active_model(self, model_type: str, model_id: str) -> bool:
        registry = self._read_json(self.registry_file)
        if model_id in registry.get('models', {}):
            registry['active'][model_type] = model_id
            # Update is_active flags
            for mid, mdata in registry['models'].items():
                if mdata.get('type') == model_type:
                    mdata['is_active'] = (mid == model_id)
            self._write_json(self.registry_file, registry)
            return True
        return False
    
    def get_active_model(self, model_type: str) -> Optional[ModelInfo]:
        registry = self._read_json(self.registry_file)
        active_id = registry.get('active', {}).get(model_type)
        if active_id:
            data = registry.get('models', {}).get(active_id)
            return ModelInfo(**data) if data else None
        return None
    
    def get_all_models(self, model_type: Optional[str] = None) -> List[ModelInfo]:
        registry = self._read_json(self.registry_file)
        models = []
        for data in registry.get('models', {}).values():
            if model_type and data.get('type') != model_type:
                continue
            try:
                models.append(ModelInfo(**data))
            except:
                continue
        return sorted(models, key=lambda m: m.created_at, reverse=True)
    
    def rollback_model(self, model_type: str, version: int = 1) -> Optional[ModelInfo]:
        models = self.get_all_models(model_type)
        if len(models) > version:
            target = models[version]
            self.set_active_model(model_type, target.id)
            return target
        return None
    
    def save_training_job(self, job: TrainingJob) -> str:
        self._append_jsonl(self.jobs_file, job.model_dump())
        return job.id
    
    def update_training_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        records = self._read_jsonl(self.jobs_file)
        updated = False
        
        for i, record in enumerate(records):
            if record.get('id') == job_id:
                records[i].update(updates)
                updated = True
                break
        
        if updated:
            self._write_jsonl(self.jobs_file, records)
        return updated
    
    def get_training_job(self, job_id: str) -> Optional[TrainingJob]:
        records = self._read_jsonl(self.jobs_file)
        for record in records:
            if record.get('id') == job_id:
                return TrainingJob(**record)
        return None
    
    def get_recent_jobs(self, limit: int = 10) -> List[TrainingJob]:
        records = self._read_jsonl(self.jobs_file)
        jobs = []
        for record in records[-limit:]:
            try:
                jobs.append(TrainingJob(**record))
            except:
                continue
        return list(reversed(jobs))


# Singleton instances
_db_instances: Dict[str, Any] = {}

def get_dataset_db(base_path: Optional[Path] = None) -> DatasetDB:
    if 'dataset' not in _db_instances:
        path = base_path or Path(__file__).parent.parent.parent / "dataset"
        _db_instances['dataset'] = DatasetDB(path)
    return _db_instances['dataset']

def get_tenant_db(base_path: Optional[Path] = None) -> TenantDB:
    if 'tenant' not in _db_instances:
        path = base_path or Path(__file__).parent.parent.parent / "data"
        _db_instances['tenant'] = TenantDB(path)
    return _db_instances['tenant']

def get_model_registry(base_path: Optional[Path] = None) -> ModelRegistryDB:
    if 'registry' not in _db_instances:
        path = base_path or Path(__file__).parent.parent.parent / "data"
        _db_instances['registry'] = ModelRegistryDB(path)
    return _db_instances['registry']
