"""
LOTLITE Real Estate - Brand Configuration
Centralized branding constants for consistent design generation
"""

# Company Information
BRAND_NAME = "LOTLITE REAL ESTATE"
BRAND_TAGLINE = "Your Dream Property Awaits"
BRAND_PHONE = "+91 90111 35889"
BRAND_WEBSITE = "www.lotlite.com"

# Brand Colors
BRAND_COLORS = {
    "primary": "#E31837",      # LOTLITE Red
    "secondary": "#000000",    # Black
    "accent": "#FFD700",       # Golden Yellow
    "white": "#FFFFFF",
    "dark": "#1A1A2E",
}

# Design Colors
DESIGN_COLORS = {
    "headline_color": "#000000",      # Black for headlines
    "highlight_color": "#FFD700",     # Golden yellow for highlights
    "accent_color": "#E31837",        # LOTLITE Red for accents  
    "subtext_color": "#FFFFFF",       # White for subtext
    "ribbon_bg_color": "#8B0000",     # Deep red for ribbons
    "contact_bg_color": "#000000",    # Black for contact bar
}

# Logo Paths
LOGO_PATHS = {
    "main": "public/lotlite-logo.png",
    "icon": "src/assets/photo/logo/lotlite-logo.png",
    "legacy": "src/assets/photo/logo/RedLotliteLogo-4cdc009c.png"
}

# Typography
BRAND_FONTS = {
    "primary": "Inter",
    "secondary": "Roboto",
    "fallback": "Arial"
}

# Contact Information
CONTACT_INFO = {
    "phone": "+91 90111 35889",
    "email": "info@lotlite.com",
    "formatted_phone": "+91 90111 35889"
}

def get_brand_context():
    """Generate brand context for AI prompts."""
    return f"""
    Brand Identity:
    - Company: {BRAND_NAME}
    - Tagline: {BRAND_TAGLINE}
    - Contact: {BRAND_PHONE}
    - Primary Color: {BRAND_COLORS['primary']} (LOTLITE Red)
    - Secondary Color: {BRAND_COLORS['secondary']} (Black)
    - Accent Color: {BRAND_COLORS['accent']} (Golden Yellow)
    
    Design Guidelines:
    - Use LOTLITE Red for call-to-action elements
    - Black for headlines and professional text
    - Golden Yellow for highlights and emphasis
    - Always include the phone number: {BRAND_PHONE}
    """

def get_default_layout_config():
    """Return default layout configuration with brand colors.
    
    Layout Structure:
    - TOP 60%: Property building image/graphic (with logo at top-left corner)
    - BOTTOM 40%: Text content (headline, phone, details)
    """
    return {
        "title_position": "center",
        "ribbon_position": "upper-center",
        "features_position": "bottom-center",
        "contact_position": "bottom",
        "logo_position": "top-left-graphic",
        "headline_color": DESIGN_COLORS["headline_color"],
        "highlight_color": DESIGN_COLORS["highlight_color"],
        "accent_color": DESIGN_COLORS["accent_color"],
        "subtext_color": DESIGN_COLORS["subtext_color"],
        "ribbon_bg_color": DESIGN_COLORS["ribbon_bg_color"],
        "contact_bg_color": DESIGN_COLORS["contact_bg_color"],
        "overlay_type": "none"
    }

def get_default_copy_template():
    """Return default copy template with brand elements."""
    return {
        "cta": BRAND_PHONE,
        "brand_name": BRAND_NAME,
        "keywords": ["ready-to-move", "luxury", "premium"]
    }
