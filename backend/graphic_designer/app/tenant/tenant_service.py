"""
Tenant Management Service
"""
from typing import Optional, List
from fastapi import HTTPException, Header, Depends
import secrets

from ..models.schemas import Tenant, TenantCreateRequest, TenantResponse
from ..models.database import get_tenant_db


class TenantService:
    """Manages multi-tenant operations."""
    
    def __init__(self):
        self.db = get_tenant_db()
    
    def create_tenant(self, request: TenantCreateRequest) -> Tenant:
        """Create a new tenant."""
        return self.db.create_tenant(request.name, request.email)
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self.db.get_tenant(tenant_id)
    
    def authenticate(self, api_key: str) -> Optional[Tenant]:
        """Authenticate tenant by API key."""
        return self.db.get_tenant_by_api_key(api_key)
    
    def check_quota(self, tenant_id: str) -> bool:
        """Check if tenant has remaining quota."""
        tenant = self.db.get_tenant(tenant_id)
        if not tenant:
            return False
        return tenant.usage_count < tenant.usage_quota
    
    def increment_usage(self, tenant_id: str) -> bool:
        """Increment tenant's usage count."""
        return self.db.update_usage(tenant_id, 1)
    
    def get_usage_stats(self, tenant_id: str) -> dict:
        """Get usage statistics for a tenant."""
        tenant = self.db.get_tenant(tenant_id)
        if not tenant:
            return {}
        
        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "usage_count": tenant.usage_count,
            "usage_quota": tenant.usage_quota,
            "remaining": tenant.usage_quota - tenant.usage_count,
            "percent_used": round((tenant.usage_count / tenant.usage_quota) * 100, 1)
        }


# Dependency for API key authentication
async def get_current_tenant(x_api_key: Optional[str] = Header(None)) -> Optional[Tenant]:
    """FastAPI dependency for tenant authentication."""
    
    if not x_api_key:
        return None  # Allow anonymous for now
    
    service = TenantService()
    tenant = service.authenticate(x_api_key)
    
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account is disabled")
    
    return tenant


async def require_tenant(x_api_key: str = Header(...)) -> Tenant:
    """FastAPI dependency that requires authentication."""
    
    service = TenantService()
    tenant = service.authenticate(x_api_key)
    
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account is disabled")
    
    if not service.check_quota(tenant.id):
        raise HTTPException(status_code=429, detail="Usage quota exceeded")
    
    return tenant


# Singleton
_tenant_service: Optional[TenantService] = None

def get_tenant_service() -> TenantService:
    global _tenant_service
    if _tenant_service is None:
        _tenant_service = TenantService()
    return _tenant_service
