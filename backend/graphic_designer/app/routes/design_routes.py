"""
Design Routes - Core design generation with ensemble selection and auto-capture

ENHANCEMENTS IMPLEMENTED:
- Font caching for performance
- Request timeout for image generation
- Retry logic with exponential backoff
- Structured logging and error handling
- Plan caching for similar inputs
"""
import os
import json
import asyncio
import base64
import uuid
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Depends
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

import google.generativeai as genai
from google.cloud import aiplatform
from google.protobuf import json_format

from ..models.schemas import (
    DesignRequest, DesignResponse, MultiDesignResponse,
    DesignPlan, DesignCopy, LayoutConfig, DesignImage,
    DatasetSample, EvaluationScores, ValidationResult
)
from ..models.database import get_dataset_db
from ..evaluators import get_evaluator
from ..validators import get_validator
from ..storage import get_storage
from ..tenant import get_current_tenant, Tenant, get_tenant_service
from ..brand import get_brand_service
from ..training import get_example_library

# ============================================================
# CONFIGURATION & INITIALIZATION
# ============================================================

router = APIRouter(prefix="/design", tags=["Design Generation"])

# Structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("design_generator")

# Config
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
IMAGEN_MODEL = "imagen-3.0-generate-001"

# Timeouts and Retry Configuration
IMAGE_GENERATION_TIMEOUT = 60  # seconds
PLAN_GENERATION_TIMEOUT = 30   # seconds
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds (exponential backoff)

# ============================================================
# CACHING LAYER
# ============================================================

# Global Font Cache - Load once, reuse
FONT_CACHE: Dict[str, ImageFont.FreeTypeFont] = {}
FONT_PATH_CACHE: Optional[str] = None

# Plan Cache - LRU cache for similar inputs
PLAN_CACHE: Dict[str, DesignPlan] = {}
PLAN_CACHE_MAX_SIZE = 100

def get_plan_cache_key(request: DesignRequest) -> str:
    """Generate cache key from request parameters."""
    key_data = f"{request.raw_input}:{request.category}:{request.platform}:{request.style}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_cached_plan(cache_key: str) -> Optional[DesignPlan]:
    """Retrieve plan from cache if exists."""
    return PLAN_CACHE.get(cache_key)

def cache_plan(cache_key: str, plan: DesignPlan):
    """Store plan in cache, maintaining max size."""
    if len(PLAN_CACHE) >= PLAN_CACHE_MAX_SIZE:
        # Remove oldest entry (simple LRU approximation)
        oldest_key = next(iter(PLAN_CACHE))
        del PLAN_CACHE[oldest_key]
    PLAN_CACHE[cache_key] = plan

# ============================================================
# INITIALIZATION
# ============================================================

# Initialize AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if PROJECT_ID:
    try:
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        logger.info(f"✅ Vertex AI initialized: {PROJECT_ID}/{LOCATION}")
    except Exception as e:
        logger.warning(f"⚠️ Vertex AI init failed: {e}")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_font_path() -> Optional[str]:
    """Get font path with caching."""
    global FONT_PATH_CACHE
    
    if FONT_PATH_CACHE is not None:
        return FONT_PATH_CACHE
    
    options = [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\seguiSB.ttf",
        "C:\\Windows\\Fonts\\impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arial.ttf"
    ]
    for path in options:
        if os.path.exists(path):
            FONT_PATH_CACHE = path
            logger.info(f"📝 Font loaded: {path}")
            return path
    
    logger.warning("⚠️ No font found, using default")
    return None


def get_cached_font(size_pt: int, base_scale: float = 1.0) -> ImageFont.FreeTypeFont:
    """Get font with caching - load once, reuse forever."""
    scaled_size = int(size_pt * base_scale)
    cache_key = f"{scaled_size}"
    
    if cache_key in FONT_CACHE:
        return FONT_CACHE[cache_key]
    
    font_path = get_font_path()
    try:
        if font_path:
            font = ImageFont.truetype(font_path, scaled_size)
        else:
            font = ImageFont.load_default()
        FONT_CACHE[cache_key] = font
        return font
    except Exception as e:
        logger.warning(f"Font load error for size {scaled_size}: {e}")
        return ImageFont.load_default()


async def retry_with_backoff(func, *args, max_retries: int = MAX_RETRIES, **kwargs):
    """Execute function with exponential backoff retry."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            wait_time = RETRY_DELAY_BASE ** attempt
            logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    logger.error(f"❌ All {max_retries} attempts failed")
    raise last_exception


async def generate_design_plan(request: DesignRequest, brand_context: str = "") -> DesignPlan:
    """Generate structured design plan using Gemini with style learning from examples."""
    
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # Get style context from training examples
    try:
        example_lib = get_example_library()
        style_context = example_lib.get_style_context(request.category)
        reference_style = example_lib.get_reference_image_description()
    except Exception as e:
        logger.warning(f"⚠️ Failed to load example library: {e}")
        style_context = ""
        reference_style = ""
    
    system_prompt = f"""
    You are a Professional Real Estate Marketing Graphic Designer specialized in creating 
    high-impact property advertisements.

    POSTER LAYOUT STRUCTURE (MUST FOLLOW):
    The poster is divided into two main sections:
    - TOP 60%: Property building image/graphic
    - BOTTOM 40%: White/light background with text content
    
    GRAPHIC SECTION (Top 60%):
    - High-quality property building image
    - LOGO: Company logo in TOP-LEFT CORNER of the entire graphic (overlaid on image)
    - Brand watermark in bottom-right corner of this section
    
    TEXT SECTION LAYOUT (Bottom 40%):
    
    2. HEADLINE (CENTER): Bold, attention-grabbing headline in the CENTER
       - Example: "READY TO MOVE FLATS AVAILABLE"
       - Use UPPERCASE for impact
       - Key words in LOTLITE Red (#E31837), other words in Black (#000000)
    
    3. PHONE NUMBER: Displayed prominently BELOW the headline
       - Centered with black background pill/button
       - White text: +91 90111 35889
       
    4. PROPERTY DETAILS (LOWER SECTION):
       - Subtext: Property type and availability info
       - Feature lines: BHK details, amenities, area, etc.
       - Mix of black text with red accent for numbers

    {reference_style}

    {style_context}

    {brand_context}

    INPUT CONTEXT:
    Property Info: {request.raw_input}
    Category: {request.category}
    Brand Info: {request.brand_info or 'LOTLITE REAL ESTATE'}
    Platform: {request.platform}
    Style: {request.style}
    Color Theme: {request.color_theme or 'professional-red-black'}
    
    ANALYZE the property info and create compelling marketing copy.

    OUTPUT FORMAT (JSON ONLY):
    {{
      "visual_prompt": "Create a clean, professional real estate property image showing modern residential building/towers with clear architectural details. Blue sky background. No text on the image.",
      "copy": {{
        "headline": "READY TO MOVE | FLATS AVAILABLE IN [LOCATION]",
        "subtext": "X BHK PREMIUM APARTMENTS",
        "feature_line_1": "Carpet Area: XXX Sq.Ft.",
        "feature_line_2": "Price: XX Lakhs | Near [Landmark]",
        "cta": "+91 90111 35889",
        "brand_name": "LOTLITE REAL ESTATE",
        "keywords": ["ready-to-move", "flats", "apartments"]
      }},
      "layout": {{
        "title_position": "center",
        "logo_position": "top-left-text-area",
        "phone_position": "center-below-headline",
        "details_position": "lower-section",
        "headline_color": "#000000",
        "highlight_color": "#FFD700",
        "accent_color": "#E31837",
        "subtext_color": "#000000",
        "contact_bg_color": "#000000",
        "overlay_type": "none"
      }},
      "reasoning": "Image on top (60%), text below (40%). Logo top-left of text area, centered headline, phone below headline, property details in lower section."
    }}
    """
    
    try:
        response = await asyncio.to_thread(
            model.generate_content,
            system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        
        data = json.loads(text)
        return DesignPlan(**data)
        
    except Exception as e:
        print(f"Plan Generation Failed: {e}")
        return DesignPlan(
            visual_prompt=f"Modern real estate photography of {request.category}",
            copy=DesignCopy(
                headline="Premium Property",
                subtext=request.raw_input[:50] if request.raw_input else "Contact for details",
                cta="Contact Us",
                keywords=[]
            ),
            layout=LayoutConfig(),
            reasoning="Fallback due to error"
        )


async def _generate_background_image_internal(visual_prompt: str, aspect_ratio: str) -> str:
    """Internal image generation function."""
    
    full_prompt = f"""
    PROMPT: {visual_prompt}
    
    QUALITY REQUIREMENTS:
    - Photorealistic, 8k resolution, architectural digest style
    - Soft natural lighting
    - NO TEXT, NO WATERMARKS, NO LOGOS on the generated image itself
    """
    
    client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    
    endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{IMAGEN_MODEL}"
    
    instances = [{"prompt": full_prompt}]
    parameters = {
        "sampleCount": 1,
        "aspectRatio": aspect_ratio,
        "safetyFilterLevel": "block_some",
        "personGeneration": "allow_adult",
        "addWatermark": False
    }
    
    response = await asyncio.to_thread(
        client.predict,
        endpoint=endpoint,
        instances=instances,
        parameters=parameters
    )
    
    predictions = response.predictions
    if not predictions:
        raise ValueError("No image generated from Imagen API")
    
    pred = predictions[0]
    
    try:
        pred_dict = dict(pred)
    except:
        try:
            pred_dict = json_format.MessageToDict(pred)
        except:
            pred_dict = {}
    
    bytes_data = pred_dict.get("bytesBase64Encoded") or pred_dict.get("bytes_base64_encoded")
    
    if not bytes_data:
        raise ValueError("Could not find base64 data in Imagen response")
    
    return bytes_data


async def generate_background_image(visual_prompt: str, aspect_ratio: str) -> str:
    """
    Generate background using Vertex AI Imagen.
    
    Features:
    - Timeout protection (60 seconds)
    - Retry with exponential backoff (3 attempts)
    - Structured error logging
    """
    
    logger.info(f"🎨 Generating image: aspect={aspect_ratio}, prompt={visual_prompt[:50]}...")
    
    try:
        # Apply timeout
        result = await asyncio.wait_for(
            retry_with_backoff(
                _generate_background_image_internal,
                visual_prompt,
                aspect_ratio,
                max_retries=MAX_RETRIES
            ),
            timeout=IMAGE_GENERATION_TIMEOUT
        )
        logger.info("✅ Image generated successfully")
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"❌ Image generation timed out after {IMAGE_GENERATION_TIMEOUT}s")
        raise HTTPException(
            status_code=504,
            detail={
                "message": "Image generation timed out",
                "stage": "background_generation",
                "timeout_seconds": IMAGE_GENERATION_TIMEOUT,
                "suggestion": "Try simplifying your input or try again later"
            }
        )
    except Exception as e:
        logger.error(f"❌ Image generation failed: {e}", extra={
            "stage": "background_gen",
            "prompt": visual_prompt[:100],
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Image generation failed",
                "stage": "background_generation",
                "error": str(e),
                "suggestion": "Try simplifying your input or check your API quota"
            }
        )


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def compose_design(background_base64: str, plan: DesignPlan, aspect_ratio: str) -> str:
    """
    Compose professional real estate poster design.
    LAYOUT STRUCTURE:
    - TOP 60%: Property building image/graphic
    - BOTTOM 40%: White/light background with text content
    - Logo: Top-left of text area
    TEXT SECTION LAYOUT (Bottom 40%):
    - Headline: Center
    - Phone: Below headline
    - Property Details: Below phone
    """
    
    image_data = base64.b64decode(background_base64)
    bg_img = Image.open(io.BytesIO(image_data))
    
    if bg_img.mode != 'RGBA':
        bg_img = bg_img.convert('RGBA')
    
    W, H = bg_img.size
    
    # Calculate graphic area (60% top) and text area (40% bottom)
    graphic_area_height = int(H * 0.60)
    text_area_start = graphic_area_height
    text_area_height = H - graphic_area_height
    
    # ============================================================
    # UNIFIED COLOR SCHEME - Image as full background with gradient overlay
    # ============================================================
    
    # Create canvas - use the property image as FULL background
    canvas = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    
    # Resize background to fill entire canvas
    bg_resized = bg_img.resize((W, H), Image.Resampling.LANCZOS)
    canvas.paste(bg_resized, (0, 0))
    
    # Create gradient overlay for bottom text area (for readability)
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Draw gradient from transparent top to semi-dark bottom for text readability
    gradient_start = int(H * 0.45)  # Start gradient at 45% from top
    for y in range(gradient_start, H):
        # Calculate opacity: 0 at start, increasing to ~200 at bottom
        progress = (y - gradient_start) / (H - gradient_start)
        opacity = int(220 * progress)  # Max opacity 220 (semi-transparent dark)
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, opacity))
    
    # Composite gradient overlay
    canvas = Image.alpha_composite(canvas, overlay)
    
    # Create new overlay for text elements
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Typography setup - USE CACHED FONTS
    base_scale = W / 1080.0
    
    # Font sizes - INCREASED for better visibility (using cached fonts)
    font_logo_text = get_cached_font(38, base_scale)
    font_headline_large = get_cached_font(70, base_scale)  # Increased from 48
    font_headline_med = get_cached_font(50, base_scale)    # Increased from 36
    font_phone = get_cached_font(40, base_scale)           # Increased from 32
    font_details = get_cached_font(38, base_scale)         # Increased from 26
    font_features = get_cached_font(40, base_scale)        # Increased from 22
    
    padding = int(30 * base_scale)
    
    # Get colors - text will be WHITE on dark gradient for visibility
    headline_color = '#FFFFFF'  # White text on dark gradient
    highlight_color = getattr(plan.layout, 'highlight_color', '#FFD700')
    accent_color = getattr(plan.layout, 'accent_color', '#E31837')
    contact_bg = getattr(plan.layout, 'contact_bg_color', '#E31837')  # Red pill for CTA
    accent_rgb = hex_to_rgb(accent_color)
    
    # ===== TOP-LEFT CORNER: LOGO (Over the graphic image) =====
    # Logo is in backend/graphic_designer/public/lotlite-logo.png
    logo_path = Path(__file__).parent.parent.parent / "public" / "lotlite-logo.png"
    
    # Fallback to absolute path
    if not logo_path.exists():
        logo_path = Path("D:/real_state_project/public/lotlite-logo.png")
    
    logo_x = padding
    logo_y = padding
    
    logger.info(f"🔍 Logo path: {logo_path}, exists: {logo_path.exists()}")
    
    try:
        if logo_path.exists():
            logo_img = Image.open(logo_path).convert('RGBA')
            
            # Scale logo by WIDTH to ensure it fits completely
            # Logo is 1024x370 (aspect ratio ~2.77)
            logo_max_w = int(220 * base_scale)  # LARGER width for full visibility
            logo_ratio = logo_max_w / logo_img.width
            logo_new_h = int(logo_img.height * logo_ratio)
            logo_new_w = logo_max_w
            logo_img = logo_img.resize((logo_new_w, logo_new_h), Image.Resampling.LANCZOS)
            
            # Create a logo layer with white background
            logo_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            logo_draw = ImageDraw.Draw(logo_layer)
            
            # Draw semi-transparent white background behind logo
            logo_bg_padding = int(15 * base_scale)
            logo_bg_rect = [
                (logo_x - logo_bg_padding, logo_y - logo_bg_padding),
                (logo_x + logo_new_w + logo_bg_padding, logo_y + logo_new_h + logo_bg_padding)
            ]
            logo_draw.rounded_rectangle(logo_bg_rect, radius=int(12 * base_scale), fill=(255, 255, 255, 245))
            
            # Paste logo on logo layer
            logo_layer.paste(logo_img, (logo_x, logo_y), logo_img)
            
            # Composite logo layer onto canvas
            canvas = Image.alpha_composite(canvas, logo_layer)
            logger.info(f"✅ Logo displayed: {logo_new_w}x{logo_new_h}")
        else:
            # Fallback: Draw brand name if logo not found
            brand_name = "LOTLITE"
            logo_bg_padding = int(10 * base_scale)
            brand_bbox = font_logo_text.getbbox(brand_name)
            logo_bg_rect = [
                (logo_x - logo_bg_padding, logo_y - logo_bg_padding),
                (logo_x + (brand_bbox[2] - brand_bbox[0]) + logo_bg_padding, logo_y + (brand_bbox[3] - brand_bbox[1]) + logo_bg_padding)
            ]
            draw.rounded_rectangle(logo_bg_rect, radius=int(8 * base_scale), fill=(255, 255, 255, 230))
            draw.text((logo_x, logo_y), brand_name, font=font_logo_text, fill=hex_to_rgb(accent_color))
    except Exception as e:
        logger.warning(f"⚠️ Logo load error: {e}")
        brand_name = "LOTLITE"
        draw.text((logo_x, logo_y), brand_name, font=font_logo_text, fill=hex_to_rgb(accent_color))
    
    # ===== TEXT AREA: MAIN HEADLINE =====
    headline = plan.copy.headline if plan.copy.headline else "READY TO MOVE FLATS AVAILABLE"
    headline = headline.upper()
    
    # Position headline in the text area - more spacing from top
    headline_y = text_area_start + int(text_area_height * 0.08)
    
    # Split headline into lines if too long
    headline_lines = []
    if "|" in headline:
        headline_lines = [p.strip() for p in headline.split("|")]
    else:
        words = headline.split()
        if len(words) > 5:
            mid = len(words) // 2
            headline_lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            headline_lines = [headline]
    
    current_y = headline_y
    for i, line in enumerate(headline_lines):
        font_to_use = font_headline_large if i == 0 else font_headline_med
        bbox = font_to_use.getbbox(line)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        x_pos = (W - line_w) // 2
        
        # Draw shadow for depth
        shadow_offset = int(3 * base_scale)
        draw.text((x_pos + shadow_offset, current_y + shadow_offset), line,
                  font=font_to_use, fill=(0, 0, 0, 40))
        
        # Draw with word-by-word coloring
        words = line.split()
        word_x = x_pos
        key_words = ['READY', 'MOVE', 'AVAILABLE', 'IMMEDIATE', 'NEW', 'LAUNCH', 'FLATS', 'LUXURY']
        for word in words:
            word_bbox = font_to_use.getbbox(word + " ")
            word_w = word_bbox[2] - word_bbox[0]
            
            if any(kw in word for kw in key_words):
                color = accent_color
            else:
                color = headline_color
            
            draw.text((word_x, current_y), word, font=font_to_use, fill=color)
            word_x += word_w
        
        current_y += line_h + int(15 * base_scale)  # MORE spacing between headline lines
    
    # ===== TEXT AREA: PHONE NUMBER =====
    phone_y = current_y + int(35 * base_scale)  # MORE margin before phone
    cta_text = plan.copy.cta if plan.copy.cta else "+91 90111 35889"
    
    phone_bbox = font_phone.getbbox(cta_text)
    phone_w = phone_bbox[2] - phone_bbox[0]
    phone_h = phone_bbox[3] - phone_bbox[1]
    phone_x = (W - phone_w) // 2
    
    # Phone background pill - more prominent
    pill_padding = int(18 * base_scale)
    pill_x1 = phone_x - pill_padding
    pill_y1 = phone_y - int(6 * base_scale)
    pill_x2 = phone_x + phone_w + pill_padding
    pill_y2 = phone_y + phone_h + int(10 * base_scale)
    
    contact_rgb = hex_to_rgb(contact_bg)
    draw.rounded_rectangle([(pill_x1, pill_y1), (pill_x2, pill_y2)], 
                           radius=int(10 * base_scale), 
                           fill=contact_rgb + (255,))
    
    draw.text((phone_x, phone_y), cta_text, font=font_phone, fill=(255, 255, 255, 255))
    
    # ===== LARGER MARGIN BEFORE PROPERTY DETAILS =====
    details_y = phone_y + phone_h + int(70 * base_scale)  # MORE spacing before details
    
    # ===== DECORATIVE SEPARATOR LINE =====
    separator_y = details_y - int(20 * base_scale)
    separator_line_len = int(200 * base_scale)
    separator_x1 = (W - separator_line_len) // 2
    separator_x2 = separator_x1 + separator_line_len
    highlight_rgb = hex_to_rgb(highlight_color)
    draw.line([(separator_x1, separator_y), (separator_x2, separator_y)], 
              fill=highlight_rgb + (220,), width=int(3 * base_scale))
    
    # ===== TEXT AREA: PROPERTY DETAILS =====
    # Subtext (property type info)
    subtext = plan.copy.subtext if plan.copy.subtext else "Premium Apartments"
    subtext = subtext.upper()
    
    subtext_bbox = font_details.getbbox(subtext)
    subtext_w = subtext_bbox[2] - subtext_bbox[0]
    subtext_h = subtext_bbox[3] - subtext_bbox[1]
    subtext_x = (W - subtext_w) // 2
    
    # White text on dark gradient
    draw.text((subtext_x, details_y), subtext, font=font_details, fill=(255, 255, 255, 255))
    
    # Feature lines with more spacing
    feature_y = details_y + subtext_h + int(25 * base_scale)  # MORE margin after subtext
    
    feature_1 = getattr(plan.copy, 'feature_line_1', None) or ""
    feature_2 = getattr(plan.copy, 'feature_line_2', None) or ""
    
    for feature_text in [feature_1, feature_2]:
        if feature_text:
            feature_text = feature_text.upper()
            feature_bbox = font_features.getbbox(feature_text)
            feature_w = feature_bbox[2] - feature_bbox[0]
            feature_h = feature_bbox[3] - feature_bbox[1]
            feature_x = (W - feature_w) // 2
            
            # Color numbers in golden yellow for visibility on dark background
            words = feature_text.split()
            word_x = feature_x
            for word in words:
                word_bbox = font_features.getbbox(word + " ")
                word_w = word_bbox[2] - word_bbox[0]
                
                if any(c.isdigit() for c in word):
                    color = highlight_color  # Golden yellow for numbers
                else:
                    color = (255, 255, 255, 255)  # White text
                
                draw.text((word_x, feature_y), word, font=font_features, fill=color)
                word_x += word_w
            
            feature_y += feature_h + int(20 * base_scale)  # MORE spacing between feature lines
    
    # Composite overlay onto canvas
    canvas = Image.alpha_composite(canvas, overlay)
    
    # Convert to RGB for saving
    final_img = canvas.convert('RGB')
    
    # Export
    buffered = io.BytesIO()
    final_img.save(buffered, format="PNG", optimize=True, quality=95)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


async def save_to_dataset(request: DesignRequest, plan: DesignPlan, 
                          image_base64: str, scores: Optional[EvaluationScores],
                          tenant_id: Optional[str]) -> str:
    """Save generation to dataset for training."""
    
    sample_id = str(uuid.uuid4())
    
    # Save image
    storage = get_storage()
    image_path = await storage.save_image(
        image_base64,
        image_id=sample_id,
        tenant_id=tenant_id,
        subfolder="generated"
    )
    
    # Create sample
    sample = DatasetSample(
        id=sample_id,
        timestamp=datetime.utcnow(),
        raw_input=request.raw_input,
        visual_prompt=plan.visual_prompt,
        category=request.category,
        platform=request.platform,
        style=request.style,
        color_theme=request.color_theme,
        layout_config=plan.layout,
        copy=plan.copy,
        image_path=image_path,
        evaluation_scores=scores,
        tenant_id=tenant_id
    )
    
    # Save to database
    db = get_dataset_db()
    db.save_sample(sample)
    
    return sample_id


# ============================================================
# ROUTES
# ============================================================

@router.post("/generate", response_model=DesignResponse)
async def generate_design(
    request: DesignRequest,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Generate a single design.
    
    Pipeline:
    1. Generate design plan (Gemini) - with caching
    2. Generate background image (Imagen) - with retry & timeout
    3. Compose final design (PIL) - with cached fonts
    4. Evaluate quality (Gemini Vision)
    5. Save to dataset
    """
    
    import time
    start_time = time.time()
    
    logger.info(f"🚀 Design generation started: {request.category}/{request.platform}")
    
    tenant_id = tenant.id if tenant else request.tenant_id
    
    # Track usage
    if tenant:
        get_tenant_service().increment_usage(tenant.id)
    
    # Get brand context if specified
    brand_context = ""
    if request.brand_kit_id:
        brand_service = get_brand_service()
        kit = brand_service.get_brand_kit(request.brand_kit_id)
        if kit:
            brand_context = brand_service.get_brand_context_for_prompt(kit)
    
    # Step 1: Plan (with caching)
    plan_start = time.time()
    cache_key = get_plan_cache_key(request)
    cached_plan = get_cached_plan(cache_key)
    
    if cached_plan and not request.brand_kit_id:  # Don't use cache if brand kit specified
        plan = cached_plan
        logger.info(f"📋 Plan retrieved from cache (key: {cache_key[:8]}...)")
    else:
        plan = await generate_design_plan(request, brand_context)
        cache_plan(cache_key, plan)
        logger.info(f"📋 Plan generated in {time.time() - plan_start:.2f}s")
    
    # Step 2: Generate background (with retry & timeout)
    image_start = time.time()
    try:
        bg_base64 = await generate_background_image(plan.visual_prompt, request.aspectRatio)
        logger.info(f"🎨 Background generated in {time.time() - image_start:.2f}s")
    except HTTPException:
        raise  # Re-raise HTTPExceptions directly
    except Exception as e:
        logger.error(f"❌ Image generation failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "message": "Image generation failed",
                "error": str(e),
                "suggestion": "Try simplifying your input or try again"
            }
        )
    
    # Step 3: Compose
    compose_start = time.time()
    try:
        final_base64 = await asyncio.to_thread(compose_design, bg_base64, plan, request.aspectRatio)
        logger.info(f"🖼️ Composition completed in {time.time() - compose_start:.2f}s")
    except Exception as e:
        logger.warning(f"⚠️ Composition failed, using raw image: {e}")
        final_base64 = bg_base64
    
    # Step 4: Validate
    validator = get_validator()
    validation = validator.validate_design(final_base64, plan, request.aspectRatio)
    
    # Step 5: Evaluate (async, don't block)
    scores = None
    if GEMINI_API_KEY:
        try:
            evaluator = get_evaluator(GEMINI_API_KEY)
            scores = await evaluator.evaluate_design(
                final_base64, plan, request.category, request.platform
            )
        except Exception as e:
            logger.warning(f"⚠️ Evaluation failed: {e}")
    
    # Step 6: Save to dataset
    design_id = await save_to_dataset(request, plan, final_base64, scores, tenant_id)
    
    total_time = time.time() - start_time
    logger.info(f"✅ Design generation completed: {design_id} in {total_time:.2f}s")
    
    return DesignResponse(
        id=design_id,
        image=DesignImage(mimeType="image/png", data=final_base64),
        plan=plan,
        meta={
            "category": request.category,
            "platform": request.platform,
            "style": request.style,
            "generated_at": datetime.utcnow().isoformat(),
            "generation_time_seconds": round(total_time, 2),
            "validation": validation.model_dump(),
            "cached_plan": cached_plan is not None
        },
        scores=scores.model_dump() if scores else None
    )


@router.post("/generate-ensemble", response_model=MultiDesignResponse)
async def generate_ensemble(
    request: DesignRequest,
    num_variations: int = 3,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Generate multiple designs and select the best one.
    
    Uses multi-gen ensemble:
    1. Generate N design variations
    2. Evaluate each with AI
    3. Select best candidate
    4. Return all with selection reasoning
    """
    
    tenant_id = tenant.id if tenant else request.tenant_id
    
    if tenant:
        get_tenant_service().increment_usage(tenant.id)
    
    # Cap variations
    num_variations = min(num_variations, 5)
    
    # Get brand context
    brand_context = ""
    if request.brand_kit_id:
        brand_service = get_brand_service()
        kit = brand_service.get_brand_kit(request.brand_kit_id)
        if kit:
            brand_context = brand_service.get_brand_context_for_prompt(kit)
    
    # Generate variations in parallel
    async def generate_one(variation_index: int) -> Dict[str, Any]:
        try:
            plan = await generate_design_plan(request, brand_context)
            bg = await generate_background_image(plan.visual_prompt, request.aspectRatio)
            final = await asyncio.to_thread(compose_design, bg, plan, request.aspectRatio)
            
            # Quick eval
            scores = None
            if GEMINI_API_KEY:
                evaluator = get_evaluator(GEMINI_API_KEY)
                scores = await evaluator.evaluate_design(final, plan, request.category, request.platform)
            
            design_id = await save_to_dataset(request, plan, final, scores, tenant_id)
            
            return {
                "id": design_id,
                "image_base64": final,
                "plan": plan,
                "scores": scores
            }
        except Exception as e:
            return {"error": str(e)}
    
    tasks = [generate_one(i) for i in range(num_variations)]
    results = await asyncio.gather(*tasks)
    
    # Filter successful generations
    designs_data = [r for r in results if "id" in r]
    
    if not designs_data:
        raise HTTPException(status_code=500, detail="All generation attempts failed")
    
    # Select best using evaluator
    selection = {"best_index": 0, "reasoning": "First successful generation"}
    if len(designs_data) > 1 and GEMINI_API_KEY:
        evaluator = get_evaluator(GEMINI_API_KEY)
        selection = await evaluator.compare_designs(
            designs_data, request.category, request.platform
        )
    
    # Build response
    designs = []
    for data in designs_data:
        designs.append(DesignResponse(
            id=data["id"],
            image=DesignImage(mimeType="image/png", data=data["image_base64"]),
            plan=data["plan"],
            meta={
                "category": request.category,
                "platform": request.platform,
                "style": request.style
            },
            scores=data["scores"].model_dump() if data.get("scores") else None
        ))
    
    return MultiDesignResponse(
        designs=designs,
        best_design_id=selection.get("best_design_id", designs[0].id),
        selection_reasoning=selection.get("reasoning", "Best quality")
    )


@router.get("/{design_id}", response_model=DesignResponse)
async def get_design(
    design_id: str,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Retrieve a previously generated design."""
    
    db = get_dataset_db()
    sample = db.get_sample(design_id)
    
    if not sample:
        raise HTTPException(status_code=404, detail="Design not found")
    
    if tenant and sample.tenant_id and sample.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Load image
    storage = get_storage()
    image_base64 = await storage.load_image(sample.image_path)
    
    return DesignResponse(
        id=sample.id,
        image=DesignImage(mimeType="image/png", data=image_base64 or ""),
        plan=DesignPlan(
            visual_prompt=sample.visual_prompt,
            copy=sample.copy,
            layout=sample.layout_config,
            reasoning="Retrieved from dataset"
        ),
        meta={
            "category": sample.category,
            "platform": sample.platform,
            "style": sample.style,
            "generated_at": sample.timestamp.isoformat() if hasattr(sample.timestamp, 'isoformat') else str(sample.timestamp)
        },
        scores=sample.evaluation_scores.model_dump() if sample.evaluation_scores else None
    )


@router.get("/")
async def list_designs(
    limit: int = 20,
    category: Optional[str] = None,
    platform: Optional[str] = None,
    style: Optional[str] = None,
    tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """List generated designs with optional filters."""
    
    db = get_dataset_db()
    tenant_id = tenant.id if tenant else None
    
    samples = db.get_all_samples(
        tenant_id=tenant_id,
        category=category,
        platform=platform,
        style=style,
        limit=limit
    )
    
    return {
        "count": len(samples),
        "designs": [
            {
                "id": s.id,
                "category": s.category,
                "platform": s.platform,
                "style": s.style,
                "headline": s.copy.headline,
                "timestamp": s.timestamp.isoformat() if hasattr(s.timestamp, 'isoformat') else str(s.timestamp),
                "score": s.evaluation_scores.average if s.evaluation_scores and hasattr(s.evaluation_scores, 'average') else None
            }
            for s in samples
        ]
    }
