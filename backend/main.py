
import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Cloud & AI Imports
from google.cloud import aiplatform
import google.generativeai as genai
from google.protobuf import json_format
from dotenv import load_dotenv

# Load environment variables from local .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- Configuration ---
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
IMAGEN_MODEL = "imagen-3.0-generate-001"

if not PROJECT_ID:
    print("WARNING: GOOGLE_CLOUD_PROJECT is not set.")

# 1. Initialize Gemini (Text) with API Key
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found.")

# 2. Initialize Vertex AI (Image) with IAM / Service Account
try:
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Failed to initialize Vertex AI: {e}")

app = FastAPI(title="Real Estate AI Graphic Designer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Contracts (The "Opinionated" Structure) ---

class DesignRequest(BaseModel):
    category: str = "ready-to-move"
    raw_input: str  # The messy user text
    aspectRatio: str = "9:16" 

class DesignCopy(BaseModel):
    headline: str
    subtext: str
    cta: str
    keywords: list[str]

class DesignImage(BaseModel):
    mimeType: str
    data: str # Base64

class DesignResponse(BaseModel):
    image: DesignImage
    design_copy: DesignCopy = Field(alias="copy") # Use alias to avoid shadowing BaseModel.copy
    meta: Dict[str, Any]

# --- Layer 3: Composition Engine (Pillow) ---

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import base64

def get_font_path():
    """Returns a valid font path for Windows."""
    # Common Windows font paths
    options = [
        "C:\\Windows\\Fonts\\arialbd.ttf", # Arial Bold
        "C:\\Windows\\Fonts\\arial.ttf",   # Arial
        "C:\\Windows\\Fonts\\seguiSB.ttf", # Segoe UI Semibold
        "arial.ttf"
    ]
    for path in options:
        if os.path.exists(path):
            return path
    return None

def compose_design(background_base64: str, copy: DesignCopy, aspect_ratio: str) -> str:
    """
    Overlays text copy onto the background image using strictly layout rules.
    """
    # 1. Decode Image
    image_data = base64.b64decode(background_base64)
    img = Image.open(io.BytesIO(image_data))
    
    # Ensure RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    W, H = img.size
    draw = ImageDraw.Draw(img)
    
    # 2. Add Dark Gradient at Bottom (For Text Contrast)
    # Create a separate layer for gradient
    gradient = Image.new('L', (W, H), 0)
    g_draw = ImageDraw.Draw(gradient)
    
    # Draw gradient from 50% height to 100% height
    for y in range(int(H * 0.5), H):
        msg_y = y - int(H * 0.5)
        alpha = int(255 * (msg_y / (H * 0.5))) # 0 to 255
        # Quadratic ease-in for smoother gradient
        alpha = int(255 * ((msg_y / (H * 0.5)) ** 1.5))
        g_draw.line([(0, y), (W, y)], fill=alpha)
        
    gradient_layer = Image.new('RGB', (W, H), (0,0,0))
    img.paste(gradient_layer, (0,0), mask=gradient)

    # 3. Typography Configuration
    font_path = get_font_path()
    
    # Scaling factors based on image width
    # 9:16 is typically narrow, 1:1 is wider relative to height
    base_scale = W / 1000.0
    
    headline_size = int(60 * base_scale)
    subtext_size = int(35 * base_scale)
    cta_size = int(30 * base_scale)
    
    try:
        font_headline = ImageFont.truetype(font_path, headline_size) if font_path else ImageFont.load_default()
        font_subtext = ImageFont.truetype(font_path, subtext_size) if font_path else ImageFont.load_default()
        font_cta = ImageFont.truetype(font_path, cta_size) if font_path else ImageFont.load_default()
    except:
        font_headline = ImageFont.load_default()
        font_subtext = ImageFont.load_default()
        font_cta = ImageFont.load_default()
        
    # 4. Layout Logic (Bottom Left Aligned)
    # Increased padding to strictly adhere to Meta/Instagram Safe Zones
    padding_x = int(100 * base_scale) # More breathing room on sides
    padding_bottom = int(220 * base_scale) # Significant bottom buffer for mobile UI/buttons
    
    # 4b. Logo Overlay (Top Left)
    logo_path = Path("D:/real_state_project/public/logo.png")
    if not logo_path.exists():
         # Fallback to relative path if absolute fails
         logo_path = Path(__file__).parent.parent / "public" / "logo.png"

    if logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Resize logo: maintain aspect ratio, target width ~25% of image width
            target_logo_w = int(W * 0.25)
            aspect = logo.height / logo.width
            target_logo_h = int(target_logo_w * aspect)
            logo = logo.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)
            
            # Position: Top Center or Top Left? requested "use logo". 
            # Standard Ad: Top Left or Center. Let's do Top Left with padding.
            logo_x = padding_x
            logo_y = int(80 * base_scale) # Top padding
            
            img.paste(logo, (logo_x, logo_y), logo)
        except Exception as e:
            print(f"Warning: Failed to process logo: {e}")
    else:
        print(f"Warning: Logo not found at {logo_path}")

    # -- CTA (Button style) --
    # Calculate text size using getbbox (left, top, right, bottom)
    cta_text = copy.cta.upper()
    left, top, right, bottom = font_cta.getbbox(cta_text)
    cta_w = right - left
    cta_h = bottom - top
    
    cta_pad_inner = int(20 * base_scale)
    cta_x = padding_x
    cta_y = H - padding_bottom - cta_h - (cta_pad_inner * 2)
    
    # Draw CTA Background
    draw.rectangle(
        [
            (cta_x, cta_y), 
            (cta_x + cta_w + (cta_pad_inner*2), cta_y + cta_h + (cta_pad_inner*2))
        ], 
        fill="#ffffff"
    )
    # Draw CTA Text
    draw.text(
        (cta_x + cta_pad_inner, cta_y + cta_pad_inner - (top * 0.2)), # Adjust for baseline
        cta_text, 
        font=font_cta, 
        fill="#000000"
    )
    
    # -- Subtext --
    subtext = copy.subtext
    # Wrap subtext if too long? For now, we assume Gemini follows word limits.
    
    # Get height estimate
    s_left, s_top, s_right, s_bottom = font_subtext.getbbox("Tg") # generic ref
    s_h = s_bottom - s_top
    
    subtext_y = cta_y - s_h - int(30 * base_scale)
    draw.text((padding_x, subtext_y), subtext, font=font_subtext, fill="#dddddd")
    
    # -- Headline --
    headline = copy.headline
    # Simple word wrap logic
    words = headline.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        # Check width
        test_line = " ".join(current_line)
        l, t, r, b = font_headline.getbbox(test_line)
        if (r - l) > (W - (padding_x * 2)):
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    lines.append(" ".join(current_line))
    
    # Draw lines upwards from subtext
    h_left, h_top, h_right, h_bottom = font_headline.getbbox("Hg")
    line_height = (h_bottom - h_top) * 1.2
    
    headline_start_y = subtext_y - (len(lines) * line_height) - int(20 * base_scale)
    
    for i, line in enumerate(lines):
        draw.text(
            (padding_x, headline_start_y + (i * line_height)), 
            line, 
            font=font_headline, 
            fill="#ffffff",
            stroke_width=2 if base_scale > 1 else 1,
            stroke_fill="#000000"
        )

    # 5. Export
    buffered = io.BytesIO()
    img.save(buffered, format="PNG", optimize=True)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# --- Data Contracts (The "Opinionated" Structure) ---

class DesignRequest(BaseModel):
    category: str = "ready-to-move"
    raw_input: str  # The messy user text
    aspectRatio: str = "9:16" 

class DesignCopy(BaseModel):
    headline: str
    subtext: str
    cta: str
    keywords: list[str]

class DesignImage(BaseModel):
    mimeType: str
    data: str # Base64

class DesignResponse(BaseModel):
    image: DesignImage
    copy: DesignCopy
    meta: Dict[str, Any]

# --- Layer 3: Composition Engine (Pillow) ---

# --- Layer 1: Copy Enhancement (Gemini via API Key) ---

async def generate_marketing_copy(raw_input: str, category: str) -> DesignCopy:
    """
    Uses Google Generative AI (API Key) to extract structured marketing copy.
    """
    # Use a standard Gemini model accessible via API Key
    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    prompt = f"""
    You are a professional Real Estate Copywriter.
    Analyze the following raw property details and extracting structured marketing copy for a visual flyer.
    
    Category: {category}
    Raw Input: "{raw_input}"
    
    Instructions:
    1. HEADLINE: catchy, premium, max 5 words. (e.g. "Luxury 3BHK in Baner")
    2. SUBTEXT: specific highlights, max 10 words. (e.g. "River view • Ready Possession • ₹2Cr")
    3. CTA: urgent action, max 3 words. (e.g. "Book Visit")
    4. KEYWORDS: extract 3 visual keywords for the image generator.
    
    Output JSON ONLY:
    {{
        "headline": "...",
        "subtext": "...",
        "cta": "...",
        "keywords": ["...", "...", "..."]
    }}
    """
    
    try:
        # Run in thread executor as genai library is synchronous
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        text = response.text.strip()
        # Cleanup markdown if present
        if text.startswith("```json"):
            text = text[7:-3]
            
        data = json.loads(text)
        return DesignCopy(**data)
        
    except Exception as e:
        print(f"Copy Generation Failed: {e}")
        # Fallback safe copy
        return DesignCopy(
            headline="Premium Property",
            subtext=raw_input[:50] + "...",
            cta="Contact Us",
            keywords=[category, "modern", "architecture"]
        )

# --- Layer 2: Image Generation (Imagen via Vertex AI IAM) ---

async def generate_background_image(category: str, keywords: list[str], aspect_ratio: str) -> str:
    """
    Generates a CLEAN background image tailored for text overlays Using Vertex AI.
    """
    
    style_map = {
        "ready-to-move": "Warm, lived-in luxury apartment interior with natural daylight",
        "under-construction": "Golden hour architectural shot of a modern building facade, aspirational",
        "luxury": "Cinematic wide shot of a high-end penthouse living room, evening mood lighting",
        "rental": "Bright, airy, clean empty room with premium flooring",
        "commercial": "Modern glass office building exterior against a blue sky, professional",
        "open-plot": "Green landscape open plot with marked boundaries, drone view"
    }
    
    base_style = style_map.get(category, "Professional real estate photography")
    visual_cues = ", ".join(keywords)
    
    # OPINIONATED PROMPT: force text overlay
    prompt = f"""
    Create a high-quality ADVERTISEMENT POSTER for real estate.
    
    VISUAL SCENE:
    high-quality real estate photography of {base_style}.
    visual details: {visual_cues}.
    
    TEXT OVERLAY INSTRUCTIONS (MANDATORY):
    - You MUST Include the following text clearly on the image:
      "PREMIUM REAL ESTATE"
    - The text must be large, legible, and integrated into the design.
    - Use modern, luxury typography.
    - Contrast the text against the background.
    
    composition constraints:
    - Clean composition
    - Photorealistic, 8k resolution, architectural digest style
    - Soft natural lighting
    
    negative constraints:
    - NO LOGOS
    - NO WATERMARKS
    - NO PEOPLE
    - NO MESSY FURNITURE
    - NO BLURRY TEXT
    """
    
    # Using the raw PredictionService for reliability with Imagen
    client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
    
    # Correct Endpoint Format for Google Publisher Models
    endpoint = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{IMAGEN_MODEL}"
    
    # Imagen 3 Request Structure
    instances = [{"prompt": prompt}]
    parameters = {
        "sampleCount": 1,
        "aspectRatio": aspect_ratio,
        "safetyFilterLevel": "block_some",
        "personGeneration": "allow_adult",
        "addWatermark": False
    }
    
    try:
        # Running blocking call in a thread for async compat
        response = await asyncio.to_thread(
            client.predict,
            endpoint=endpoint,
            instances=instances,
            parameters=parameters
        )
        
        # Extract
        predictions = response.predictions
        if not predictions:
            raise ValueError("No image generated")
            
        pred = predictions[0] # This is likely a MapComposite
        
        # Convert MapComposite/Protobuf to standard dict
        try:
            # If it's already a dict/MapComposite, this usually works
            pred_dict = dict(pred)
        except:
            # Fallback for raw protobuf message
            try:
                pred_dict = json_format.MessageToDict(pred)
            except:
                pred_dict = {}

        # Debug logs
        print(f"DEBUG keys: {list(pred_dict.keys())}")
        
        bytes_data = pred_dict.get("bytesBase64Encoded")
        
        # Support "bytes_base64_encoded" snake_case variant
        if not bytes_data:
             bytes_data = pred_dict.get("bytes_base64_encoded")

        if not bytes_data:
             # Try nested struct value common in older models or wrapped responses
             # structure: { struct_value: { fields: { bytesBase64Encoded: { string_value: ... } } } }
             # But MapComposite usually flattens this.
             print(f"DEBUG FULL PRED: {pred_dict}")
             raise ValueError("Could not find base64 data in response")

        return bytes_data

    except Exception as e:
         # Check for 404/Publisher errors specifically to give better hints
         error_str = str(e)
         if "publisher" in error_str and "unexpected keyword" in error_str:
             print("CRITICAL: Endpoint path construction error. Trying alternative...")
             # Retry logic or fail explicit
         raise e


# --- Pipeline Orchestrator ---

@app.post("/generate-design", response_model=DesignResponse)
async def generate_design_pipeline(request: DesignRequest):
    print(f"🎨 Starting Graphic Design Pipeline for: {request.category}")
    
    # Step 1: Generate Content (Gemini API Key)
    print("📝 Step 1: Enhancing Copy (Gemini API)...")
    copy_data = await generate_marketing_copy(request.raw_input, request.category)
    print(f"   Headline: {copy_data.headline}")
    
    # Step 2: Generate Visual (Vertex AI IAM)
    print("🖼️ Step 2: Generating Background Image (Imagen)...")
    try:
        bg_base64 = await generate_background_image(
            request.category, 
            copy_data.keywords, 
            request.aspectRatio
        )
    except Exception as e:
        print(f"Image Gen Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")

    # Step 3: Composition (Python PIL)
    print("🎨 Step 3: Composing Design (Pillow)...")
    try:
        final_base64 = await asyncio.to_thread(
             compose_design, bg_base64, copy_data, request.aspectRatio
        )
    except Exception as e:
        print(f"Composition Error: {e}")
        # Fallback to background only if composition fails
        final_base64 = bg_base64

    # Step 4: Assemble Response
    print("🚀 Pipeline Complete.")
    
    return DesignResponse(
        image=DesignImage(
            mimeType="image/png",
            data=final_base64
        ),
        copy=copy_data,
        meta={
            "category": request.category,
            "generated_at": "now",
            "model": IMAGEN_MODEL,
            "pipeline": "production-hybrid"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
