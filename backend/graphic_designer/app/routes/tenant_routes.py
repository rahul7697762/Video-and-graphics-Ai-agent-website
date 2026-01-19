"""
Tenant and Brand Kit Routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional, List

from ..models.schemas import (
    Tenant, TenantCreateRequest, TenantResponse, BrandKit
)
from ..tenant import get_tenant_service, get_current_tenant, require_tenant
from ..brand import get_brand_service

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("/register", response_model=TenantResponse)
async def register_tenant(request: TenantCreateRequest):
    """Register a new tenant and receive an API key."""
    
    service = get_tenant_service()
    tenant = service.create_tenant(request)
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        email=tenant.email,
        api_key=tenant.api_key,
        created_at=tenant.created_at
    )


@router.get("/me")
async def get_current_tenant_info(tenant: Tenant = Depends(require_tenant)):
    """Get current tenant information."""
    
    service = get_tenant_service()
    stats = service.get_usage_stats(tenant.id)
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "email": tenant.email,
        "created_at": tenant.created_at.isoformat() if hasattr(tenant.created_at, 'isoformat') else str(tenant.created_at),
        "usage": stats
    }


@router.get("/usage")
async def get_usage_stats(tenant: Tenant = Depends(require_tenant)):
    """Get usage statistics for current tenant."""
    
    service = get_tenant_service()
    return service.get_usage_stats(tenant.id)


# Brand Kit Routes
@router.post("/brand-kits", response_model=BrandKit)
async def create_brand_kit(
    name: str,
    primary_color: str = "#000000",
    secondary_color: str = "#ffffff",
    accent_color: str = "#FFD700",
    font_family: str = "Arial",
    tagline: Optional[str] = None,
    tenant: Tenant = Depends(require_tenant)
):
    """Create a new brand kit."""
    
    service = get_brand_service()
    kit = service.create_brand_kit(
        tenant_id=tenant.id,
        name=name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        accent_color=accent_color,
        font_family=font_family,
        tagline=tagline
    )
    
    return kit


@router.get("/brand-kits", response_model=List[BrandKit])
async def list_brand_kits(tenant: Tenant = Depends(require_tenant)):
    """List all brand kits for current tenant."""
    
    service = get_brand_service()
    return service.get_tenant_brand_kits(tenant.id)


@router.get("/brand-kits/{kit_id}", response_model=BrandKit)
async def get_brand_kit(
    kit_id: str,
    tenant: Tenant = Depends(require_tenant)
):
    """Get a specific brand kit."""
    
    service = get_brand_service()
    kit = service.get_brand_kit(kit_id)
    
    if not kit:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    
    if kit.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return kit


@router.post("/brand-kits/{kit_id}/logo")
async def upload_brand_logo(
    kit_id: str,
    file: UploadFile = File(...),
    tenant: Tenant = Depends(require_tenant)
):
    """Upload a logo for a brand kit."""
    
    service = get_brand_service()
    kit = service.get_brand_kit(kit_id)
    
    if not kit:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    
    if kit.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Read file
    contents = await file.read()
    
    # Upload logo
    logo_path = await service.upload_logo(kit_id, contents, file.filename)
    
    return {
        "message": "Logo uploaded successfully",
        "logo_path": logo_path
    }
