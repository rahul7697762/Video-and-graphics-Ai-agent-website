"""
AI Evaluator Service - Uses Gemini Vision to score generated designs
"""
import json
import base64
import asyncio
from typing import Optional, Dict, Any

import google.generativeai as genai

from ..models.schemas import EvaluationScores, DesignPlan


class DesignEvaluator:
    """Evaluates generated designs using Gemini Vision."""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def evaluate_design(self, 
                               image_base64: str,
                               plan: DesignPlan,
                               category: str,
                               platform: str) -> EvaluationScores:
        """Evaluate a generated design image."""
        
        prompt = f"""
        You are an expert Real Estate Marketing Design Evaluator.
        
        Analyze the provided real estate marketing design image and rate it on these criteria (0-10 scale):
        
        1. PHOTOREALISM (0-10): How realistic and high-quality does the property/architecture look?
           - 0: Very fake/AI-looking
           - 5: Acceptable but noticeable artifacts
           - 10: Indistinguishable from professional photography
        
        2. LAYOUT_ALIGNMENT (0-10): How well organized is the visual composition?
           - Are text elements properly positioned?
           - Is there good balance between image and text?
           - Are margins/padding consistent?
        
        3. READABILITY (0-10): How easy is it to read all text elements?
           - Is contrast sufficient?
           - Are fonts appropriately sized?
           - Do text elements overlap with busy backgrounds?
        
        4. REAL_ESTATE_RELEVANCE (0-10): How appropriate is this for real estate marketing?
           - Does it look professional for property listings?
           - Would a real estate agent use this?
           - Does it convey trust and quality?
        
        5. OVERALL_QUALITY (0-10): Overall impression as a marketing asset.
        
        CONTEXT:
        - Property Category: {category}
        - Target Platform: {platform}
        - Intended Headline: {plan.copy.headline}
        - Intended Subtext: {plan.copy.subtext}
        
        OUTPUT JSON ONLY:
        {{
            "photorealism": 0-10,
            "layout_alignment": 0-10,
            "readability": 0-10,
            "real_estate_relevance": 0-10,
            "overall_quality": 0-10,
            "feedback": "Brief feedback for improvement"
        }}
        """
        
        try:
            # Prepare image for Gemini
            image_part = {
                "mime_type": "image/png",
                "data": image_base64
            }
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, image_part],
                generation_config={"response_mime_type": "application/json"}
            )
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            
            data = json.loads(text)
            
            return EvaluationScores(
                photorealism=float(data.get('photorealism', 5)),
                layout_alignment=float(data.get('layout_alignment', 5)),
                readability=float(data.get('readability', 5)),
                real_estate_relevance=float(data.get('real_estate_relevance', 5)),
                overall_quality=float(data.get('overall_quality', 5))
            )
            
        except Exception as e:
            print(f"Evaluation Error: {e}")
            # Return neutral scores on error
            return EvaluationScores(
                photorealism=5.0,
                layout_alignment=5.0,
                readability=5.0,
                real_estate_relevance=5.0,
                overall_quality=5.0
            )
    
    async def compare_designs(self, 
                               designs: list,
                               category: str,
                               platform: str) -> Dict[str, Any]:
        """Compare multiple designs and select the best one."""
        
        if len(designs) == 1:
            return {
                "best_index": 0,
                "best_design_id": designs[0].get('id'),
                "reasoning": "Single design provided"
            }
        
        # Build comparison prompt
        prompt = f"""
        You are comparing {len(designs)} real estate marketing designs.
        
        Context:
        - Property Category: {category}
        - Target Platform: {platform}
        
        For each design, evaluate:
        1. Visual quality
        2. Professional appeal
        3. Readability
        4. Brand consistency
        
        Select the BEST design by index (0-based).
        
        OUTPUT JSON ONLY:
        {{
            "best_index": 0,
            "reasoning": "Brief explanation of why this design is best",
            "rankings": [list of indices from best to worst]
        }}
        """
        
        try:
            # Prepare images
            content = [prompt]
            for i, design in enumerate(designs):
                content.append({
                    "mime_type": "image/png",
                    "data": design.get('image_base64', '')
                })
                content.append(f"Design {i}")
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                content,
                generation_config={"response_mime_type": "application/json"}
            )
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            
            data = json.loads(text)
            best_idx = int(data.get('best_index', 0))
            
            return {
                "best_index": best_idx,
                "best_design_id": designs[best_idx].get('id') if best_idx < len(designs) else designs[0].get('id'),
                "reasoning": data.get('reasoning', 'Selected based on overall quality'),
                "rankings": data.get('rankings', list(range(len(designs))))
            }
            
        except Exception as e:
            print(f"Comparison Error: {e}")
            return {
                "best_index": 0,
                "best_design_id": designs[0].get('id'),
                "reasoning": f"Fallback selection due to error: {str(e)}"
            }
    
    async def extract_features_from_example(self, 
                                            image_base64: str,
                                            additional_context: Optional[str] = None) -> Dict[str, Any]:
        """Extract design features from an example image for training."""
        
        prompt = f"""
        Analyze this real estate marketing design example and extract its characteristics.
        
        {f"Additional Context: {additional_context}" if additional_context else ""}
        
        Extract:
        1. Layout structure (where are elements positioned)
        2. Color scheme
        3. Typography style
        4. Visual composition techniques
        5. Target audience impression
        6. Effective elements
        7. Suggested improvements
        
        OUTPUT JSON ONLY:
        {{
            "layout": {{
                "title_position": "top-left/top-center/top-right/bottom-left/etc",
                "price_position": "bottom-right/etc",
                "logo_position": "bottom-left/etc",
                "visual_hierarchy": "description of visual flow"
            }},
            "colors": {{
                "primary": "#hex",
                "secondary": "#hex", 
                "accent": "#hex",
                "text_color": "#hex",
                "background_type": "solid/gradient/image"
            }},
            "typography": {{
                "headline_style": "bold/light/serif/sans-serif",
                "estimated_sizes": "large/medium/small ratios",
                "font_hierarchy": "description"
            }},
            "style": "luxury/modern/minimalist/corporate/etc",
            "category": "ready-to-move/luxury/rental/commercial/etc",
            "platform_guess": "Instagram/Facebook/Print/etc",
            "quality_score": 0-10,
            "effective_elements": ["list", "of", "working elements"],
            "improvements": ["list", "of", "suggestions"],
            "training_prompt": "A prompt that could reproduce this style"
        }}
        """
        
        try:
            image_part = {
                "mime_type": "image/png",
                "data": image_base64
            }
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, image_part],
                generation_config={"response_mime_type": "application/json"}
            )
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            
            return json.loads(text)
            
        except Exception as e:
            print(f"Feature Extraction Error: {e}")
            return {
                "error": str(e),
                "layout": {"title_position": "top-center"},
                "style": "modern",
                "quality_score": 5
            }


# Singleton
_evaluator: Optional[DesignEvaluator] = None

def get_evaluator(api_key: str) -> DesignEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = DesignEvaluator(api_key)
    return _evaluator
