"""
Example Designs - Reference images for training and style matching
Uses images from: D:/real_state_project/backend/graphic_designer/dataset/images
"""
import os
import base64
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("training")

# Dataset paths
DATASET_ROOT = Path(__file__).parent.parent.parent / "dataset"
IMAGES_DIR = DATASET_ROOT / "images"
METADATA_FILE = DATASET_ROOT / "metadata.jsonl"


@dataclass
class ExampleDesign:
    """Reference design example for training."""
    id: str
    image_path: str
    category: str
    style: str
    platform: str
    headline: str
    subtext: str
    features: List[str]
    quality_score: float
    is_approved: bool


class ExampleDesignLibrary:
    """Library of reference design examples for training."""
    
    def __init__(self):
        self.examples: List[ExampleDesign] = []
        self.reference_images: Dict[str, str] = {}  # image_name -> base64
        self._load_reference_images()
        self._load_metadata()
    
    def _load_reference_images(self):
        """Load reference images from dataset/images folder."""
        if not IMAGES_DIR.exists():
            logger.warning(f"Images directory not found: {IMAGES_DIR}")
            return
        
        # Load reference images (img1.jpeg - img8.jpeg)
        for img_file in IMAGES_DIR.glob("img*.jpeg"):
            try:
                with open(img_file, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                    self.reference_images[img_file.stem] = img_data
                    logger.info(f"📷 Loaded reference image: {img_file.name}")
            except Exception as e:
                logger.error(f"Failed to load {img_file}: {e}")
        
        logger.info(f"✅ Loaded {len(self.reference_images)} reference images")
    
    def _load_metadata(self):
        """Load design metadata from JSONL file."""
        if not METADATA_FILE.exists():
            logger.warning(f"Metadata file not found: {METADATA_FILE}")
            return
        
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self._parse_example(data)
            
            logger.info(f"✅ Loaded {len(self.examples)} design examples")
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
    
    def _parse_example(self, data: Dict[str, Any]):
        """Parse a single example from metadata."""
        try:
            # Calculate quality score
            scores = data.get("evaluation_scores", {})
            quality_score = scores.get("overall_quality", 5.0)
            
            # Check if approved
            feedback = data.get("feedback", {})
            is_approved = (
                data.get("selected_for_training", False) or
                (feedback and feedback.get("feedback_type") == "approve")
            )
            
            # Extract features
            copy_data = data.get("copy", {})
            features = [
                copy_data.get("feature_line_1", ""),
                copy_data.get("feature_line_2", "")
            ]
            features = [f for f in features if f]
            
            example = ExampleDesign(
                id=data.get("id", ""),
                image_path=data.get("image_path", ""),
                category=data.get("category", "ready-to-move"),
                style=data.get("style", "modern"),
                platform=data.get("platform", "Instagram Story"),
                headline=copy_data.get("headline", ""),
                subtext=copy_data.get("subtext", ""),
                features=features,
                quality_score=quality_score,
                is_approved=is_approved
            )
            
            self.examples.append(example)
        except Exception as e:
            logger.warning(f"Failed to parse example: {e}")
    
    def get_top_examples(self, n: int = 5, category: Optional[str] = None) -> List[ExampleDesign]:
        """Get top N examples sorted by quality score."""
        filtered = self.examples
        
        if category:
            filtered = [e for e in filtered if e.category == category]
        
        # Sort by quality score (descending)
        sorted_examples = sorted(filtered, key=lambda x: x.quality_score, reverse=True)
        
        return sorted_examples[:n]
    
    def get_approved_examples(self) -> List[ExampleDesign]:
        """Get only approved examples for training."""
        return [e for e in self.examples if e.is_approved]
    
    def get_reference_image(self, name: str) -> Optional[str]:
        """Get a reference image by name (e.g., 'img1')."""
        return self.reference_images.get(name)
    
    def get_random_reference_image(self) -> Optional[str]:
        """Get a random reference image for style matching."""
        import random
        if self.reference_images:
            key = random.choice(list(self.reference_images.keys()))
            return self.reference_images[key]
        return None
    
    def get_style_context(self, category: str = "ready-to-move") -> str:
        """Generate style context from top examples for AI prompt."""
        top_examples = self.get_top_examples(n=3, category=category)
        
        if not top_examples:
            return ""
        
        context_lines = [
            "\n--- STYLE REFERENCE FROM TOP DESIGNS ---",
            "Learn from these high-quality design patterns:"
        ]
        
        for i, ex in enumerate(top_examples, 1):
            context_lines.append(f"""
Example {i} (Score: {ex.quality_score}/10):
- Headline: "{ex.headline}"
- Subtext: "{ex.subtext}"
- Features: {', '.join(ex.features)}
- Platform: {ex.platform}
""")
        
        context_lines.append("--- END STYLE REFERENCE ---\n")
        
        return "\n".join(context_lines)
    
    def get_reference_image_description(self) -> str:
        """Describe the style of reference images for AI prompting."""
        return """
REFERENCE DESIGN STYLE GUIDE:
Based on proven high-performing real estate marketing designs:

1. LAYOUT PATTERN:
   - Full property image as background (gradient overlay for text readability)
   - Bold headline at top (mixed colors for emphasis)
   - Feature pill/ribbon in center
   - Property details in bottom section
   - Phone number in prominent CTA button
   - Logo at top-left corner

2. COLOR SCHEME:
   - Primary: LOTLITE Red (#E31837) for key words
   - Secondary: Black (#000000) for text
   - Accent: Golden Yellow (#FFD700) for numbers/highlights
   - White text on dark gradients

3. TYPOGRAPHY STYLE:
   - Bold, all-caps headlines
   - Clear hierarchy (headline > subtext > details)
   - High contrast for readability

4. VISUAL ELEMENTS:
   - High-quality property building images
   - Gradient overlays (sunset/evening mood)
   - Pill/ribbon style for key info ("LIMITED 3 BHK AVAILABLE")
   - Phone icon with contact number
"""


# Singleton instance
_library_instance: Optional[ExampleDesignLibrary] = None


def get_example_library() -> ExampleDesignLibrary:
    """Get singleton instance of example design library."""
    global _library_instance
    if _library_instance is None:
        _library_instance = ExampleDesignLibrary()
    return _library_instance
