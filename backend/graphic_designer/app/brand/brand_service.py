"""
Brand Kit Management Service
"""
from typing import Optional, List
import base64
from pathlib import Path

from ..models.schemas import BrandKit
from ..models.database import get_tenant_db
from ..storage import get_storage


class BrandKitService:
    """Manages brand kits for tenants."""
    
    def __init__(self, project_id: Optional[str] = None, gcs_bucket: Optional[str] = None):
        self.db = get_tenant_db()
        self.storage = get_storage(project_id, gcs_bucket)
    
    def create_brand_kit(self,
                         tenant_id: str,
                         name: str,
                         primary_color: str = "#000000",
                         secondary_color: str = "#ffffff",
                         accent_color: str = "#FFD700",
                         font_family: str = "Arial",
                         tagline: Optional[str] = None) -> BrandKit:
        """Create a new brand kit for a tenant."""
        
        kit = BrandKit(
            tenant_id=tenant_id,
            name=name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
            font_family=font_family,
            tagline=tagline
        )
        
        self.db.create_brand_kit(kit)
        return kit
    
    async def upload_logo(self,
                          brand_kit_id: str,
                          logo_data: bytes,
                          filename: str) -> str:
        """Upload a logo for a brand kit."""
        
        kit = self.db.get_brand_kit(brand_kit_id)
        if not kit:
            raise ValueError(f"Brand kit not found: {brand_kit_id}")
        
        # Save logo
        logo_base64 = base64.b64encode(logo_data).decode('utf-8')
        logo_path = await self.storage.save_image(
            logo_base64,
            image_id=f"logo_{brand_kit_id}",
            tenant_id=kit.tenant_id,
            subfolder="logos"
        )
        
        # Update kit with logo path
        # (Would need to add update method to DB)
        kit.logo_path = logo_path
        
        return logo_path
    
    def get_brand_kit(self, kit_id: str) -> Optional[BrandKit]:
        """Get a brand kit by ID."""
        return self.db.get_brand_kit(kit_id)
    
    def get_tenant_brand_kits(self, tenant_id: str) -> List[BrandKit]:
        """Get all brand kits for a tenant."""
        return self.db.get_tenant_brand_kits(tenant_id)
    
    def apply_brand_to_layout(self, 
                               brand_kit: BrandKit,
                               layout_config: dict) -> dict:
        """Apply brand kit colors to layout configuration."""
        
        branded_layout = layout_config.copy()
        
        # Apply brand colors
        branded_layout['headline_color'] = brand_kit.secondary_color
        branded_layout['accent_color'] = brand_kit.accent_color
        
        # Could also apply font preferences here
        
        return branded_layout
    
    def get_brand_context_for_prompt(self, brand_kit: BrandKit) -> str:
        """Generate brand context string for AI prompts."""
        
        context = f"""
        Brand Identity:
        - Name: {brand_kit.name}
        - Primary Color: {brand_kit.primary_color}
        - Secondary Color: {brand_kit.secondary_color}
        - Accent Color: {brand_kit.accent_color}
        - Font Style: {brand_kit.font_family}
        """
        
        if brand_kit.tagline:
            context += f"- Tagline: {brand_kit.tagline}\n"
        
        return context.strip()


# Singleton
_brand_service: Optional[BrandKitService] = None

def get_brand_service(project_id: Optional[str] = None,
                      gcs_bucket: Optional[str] = None) -> BrandKitService:
    global _brand_service
    if _brand_service is None:
        _brand_service = BrandKitService(project_id, gcs_bucket)
    return _brand_service
