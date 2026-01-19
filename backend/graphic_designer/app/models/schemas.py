"""
Pydantic Schemas for the Real Estate Graphic Designer SaaS
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


# --- Enums ---

class PropertyCategory(str, Enum):
    READY_TO_MOVE = "ready-to-move"
    UNDER_CONSTRUCTION = "under-construction"
    LUXURY = "luxury"
    RENTAL = "rental"
    COMMERCIAL = "commercial"
    OPEN_PLOT = "open-plot"


class DesignStyle(str, Enum):
    LUXURY = "luxury"
    MINIMALIST = "minimalist"
    MODERN = "modern"
    PREMIUM = "premium"
    CORPORATE = "corporate"
    RENTAL_FRIENDLY = "rental-friendly"


class Platform(str, Enum):
    INSTAGRAM_STORY = "Instagram Story"
    INSTAGRAM_POST = "Instagram Post"
    FACEBOOK = "Facebook"
    WEBSITE_BANNER = "Website Banner"
    PRINT_FLYER_A4 = "Print Flyer A4"
    LINKEDIN = "LinkedIn"


class FeedbackType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"


class TrainingStatus(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Core Design Schemas ---

class DesignCopy(BaseModel):
    headline: str
    subtext: str
    cta: str
    keywords: List[str] = []
    # New fields for professional poster layout
    feature_line_1: Optional[str] = None
    feature_line_2: Optional[str] = None
    brand_name: Optional[str] = None


class LayoutConfig(BaseModel):
    title_position: str = "top-center"
    price_position: str = "bottom-right"
    logo_position: str = "bottom-left"
    headline_color: str = "#1B3A5F"  # Navy blue
    subtext_color: str = "#FFFFFF"
    accent_color: str = "#C41E3A"  # Red accent
    overlay_type: str = "none"
    # New fields for professional poster layout
    ribbon_position: str = "upper-center"
    features_position: str = "bottom-center"
    contact_position: str = "bottom"
    highlight_color: str = "#FFD700"  # Golden yellow
    ribbon_bg_color: str = "#8B0000"  # Deep red
    contact_bg_color: str = "#1B3A5F"  # Navy blue


class DesignPlan(BaseModel):
    visual_prompt: str
    copy: DesignCopy
    layout: LayoutConfig
    reasoning: str


class DesignImage(BaseModel):
    mimeType: str
    data: str  # Base64


# --- Request/Response Schemas ---

class DesignRequest(BaseModel):
    category: str = "ready-to-move"
    raw_input: str
    aspectRatio: str = "9:16"
    brand_info: Optional[str] = None
    platform: str = "Instagram Story"
    style: str = "modern"
    color_theme: Optional[str] = None
    tenant_id: Optional[str] = None
    brand_kit_id: Optional[str] = None
    num_variations: int = 1  # For ensemble mode


class DesignResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    image: DesignImage
    plan: DesignPlan
    meta: Dict[str, Any]
    scores: Optional[Dict[str, float]] = None


class MultiDesignResponse(BaseModel):
    designs: List[DesignResponse]
    best_design_id: str
    selection_reasoning: str


# --- Evaluation Schemas ---

class EvaluationScores(BaseModel):
    photorealism: float = Field(ge=0, le=10)
    layout_alignment: float = Field(ge=0, le=10)
    readability: float = Field(ge=0, le=10)
    real_estate_relevance: float = Field(ge=0, le=10)
    overall_quality: float = Field(ge=0, le=10)
    
    @property
    def average(self) -> float:
        return (self.photorealism + self.layout_alignment + self.readability + 
                self.real_estate_relevance + self.overall_quality) / 5


# --- Feedback Schemas ---

class FeedbackRequest(BaseModel):
    design_id: str
    feedback_type: FeedbackType
    rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    corrections: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    design_id: str
    status: str
    message: str


# --- Training Schemas ---

class TrainingRequest(BaseModel):
    model_type: str = "imagen"  # imagen or gemini
    dataset_filter: Optional[Dict[str, Any]] = None
    epochs: int = 100
    learning_rate: float = 1e-4
    tenant_id: Optional[str] = None


class TrainingJob(BaseModel):
    id: str
    status: TrainingStatus
    model_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
    error: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    type: str
    version: str
    created_at: datetime
    is_active: bool
    metrics: Optional[Dict[str, float]] = None
    gcs_path: Optional[str] = None


# --- Dataset Schemas ---

class DatasetSample(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_input: str
    visual_prompt: str
    category: str
    platform: str
    style: str
    color_theme: Optional[str]
    layout_config: LayoutConfig
    copy: DesignCopy
    image_path: str
    evaluation_scores: Optional[EvaluationScores] = None
    feedback: Optional[Dict[str, Any]] = None
    selected_for_training: bool = False
    tenant_id: Optional[str] = None


class DatasetStats(BaseModel):
    total_samples: int
    approved_samples: int
    rejected_samples: int
    pending_samples: int
    avg_score: float
    category_distribution: Dict[str, int]
    platform_distribution: Dict[str, int]
    style_distribution: Dict[str, int]


# --- Example Upload Schemas ---

class ExampleUploadRequest(BaseModel):
    brand_info: Optional[str] = None
    labels: Optional[List[str]] = None
    category: Optional[str] = None
    style: Optional[str] = None
    tenant_id: Optional[str] = None


class ExampleUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    extracted_features: Optional[Dict[str, Any]] = None


# --- Tenant & Brand Schemas ---

class BrandKit(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    primary_color: str = "#000000"
    secondary_color: str = "#ffffff"
    accent_color: str = "#FFD700"
    logo_path: Optional[str] = None
    font_family: str = "Arial"
    tagline: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Tenant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    api_key: str
    brand_kits: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    usage_quota: int = 1000
    usage_count: int = 0


class TenantCreateRequest(BaseModel):
    name: str
    email: str


class TenantResponse(BaseModel):
    id: str
    name: str
    email: str
    api_key: str
    created_at: datetime


# --- Validation Schemas ---

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    auto_corrections: Dict[str, Any] = {}


class LayoutValidationConfig(BaseModel):
    min_font_size: int = 12
    min_contrast_ratio: float = 4.5
    min_padding_percent: float = 5.0
    cta_overlap_threshold: float = 0.1
