"""
Real Estate AI Graphic Designer - SaaS Backend
Production-ready FastAPI service with self-training capabilities

Version: 2.0.0
"""
import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import route modules
from app.routes import (
    design_router,
    feedback_router,
    training_router,
    tenant_router,
    example_router
)

# Import for backward compatibility (existing /generate-design endpoint)
from app.routes.design_routes import generate_design, DesignRequest, DesignResponse

# Load environment
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print("=" * 60)
    print("🏠 Real Estate AI Graphic Designer SaaS")
    print("=" * 60)
    print(f"📦 Version: 2.0.0")
    print(f"🔧 Project: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not configured')}")
    print(f"📍 Location: {os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}")
    print("=" * 60)
    print("\n📚 Available Endpoints:")
    print("  POST /generate-design          - Quick design generation")
    print("  POST /api/v2/design/generate   - Full design with capture")
    print("  POST /api/v2/design/generate-ensemble - Multi-gen best-of-N")
    print("  POST /api/v2/feedback/         - Submit design feedback")
    print("  POST /api/v2/training/train-model - Start LoRA training")
    print("  POST /api/v2/examples/upload   - Upload example designs")
    print("  POST /api/v2/tenants/register  - Register new tenant")
    print("\n🚀 Server starting...")
    print("=" * 60)
    
    yield
    
    print("\n👋 Server shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Real Estate AI Graphic Designer",
    description="""
    AI-powered graphic design automation for real estate marketing.
    
    ## Features
    - **Design Generation**: Create professional marketing creatives from text descriptions
    - **Multi-Gen Ensemble**: Generate N variations and auto-select the best
    - **AI Evaluation**: Automatic quality scoring using Gemini Vision
    - **Self-Training**: Capture data and fine-tune models with LoRA
    - **Multi-Tenant**: API key authentication and brand kit support
    - **Example Learning**: Upload designs for the AI to learn from
    
    ## Quick Start
    1. Call POST /generate-design with raw property details
    2. Receive AI-generated marketing creative
    3. Submit feedback to improve quality
    
    ## Training
    1. Generate designs and submit feedback
    2. Upload example designs
    3. Call POST /api/v2/training/train-model to fine-tune
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v2 routes
app.include_router(design_router, prefix="/api/v2")
app.include_router(feedback_router, prefix="/api/v2")
app.include_router(training_router, prefix="/api/v2")
app.include_router(tenant_router, prefix="/api/v2")
app.include_router(example_router, prefix="/api/v2")


# --- Backward Compatible Endpoints ---

@app.post("/generate-design", response_model=DesignResponse)
async def legacy_generate_design(request: DesignRequest):
    """
    Legacy endpoint for backward compatibility.
    Redirects to the new /api/v2/design/generate endpoint.
    """
    return await generate_design(request, tenant=None)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "graphic-designer",
        "version": "2.0.0",
        "features": [
            "design_generation",
            "ensemble_selection",
            "ai_evaluation",
            "dataset_capture",
            "lora_training",
            "multi_tenant",
            "brand_kits",
            "example_learning"
        ]
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Real Estate AI Graphic Designer",
        "version": "2.0.0",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "v1_legacy": {
                "generate": "POST /generate-design"
            },
            "v2": {
                "design": {
                    "generate": "POST /api/v2/design/generate",
                    "ensemble": "POST /api/v2/design/generate-ensemble",
                    "list": "GET /api/v2/design/",
                    "get": "GET /api/v2/design/{id}"
                },
                "feedback": {
                    "submit": "POST /api/v2/feedback/",
                    "get": "GET /api/v2/feedback/{design_id}",
                    "stats": "GET /api/v2/feedback/stats/summary"
                },
                "training": {
                    "start": "POST /api/v2/training/train-model",
                    "status": "GET /api/v2/training/training-status/{job_id}",
                    "jobs": "GET /api/v2/training/jobs",
                    "models": "GET /api/v2/training/models",
                    "dataset_stats": "GET /api/v2/training/dataset/stats"
                },
                "tenants": {
                    "register": "POST /api/v2/tenants/register",
                    "me": "GET /api/v2/tenants/me",
                    "brand_kits": "GET /api/v2/tenants/brand-kits"
                },
                "examples": {
                    "upload": "POST /api/v2/examples/upload",
                    "batch": "POST /api/v2/examples/upload-batch",
                    "list": "GET /api/v2/examples/"
                }
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8003"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
