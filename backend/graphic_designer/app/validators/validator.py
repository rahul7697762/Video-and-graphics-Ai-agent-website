"""
Layout Validator - Ensures designs meet quality standards before export
"""
from typing import Tuple, List, Dict, Any
from PIL import Image, ImageDraw
import io
import base64
import colorsys
import math

from ..models.schemas import ValidationResult, LayoutConfig, DesignPlan


class LayoutValidator:
    """Validates layout constraints and design quality."""
    
    def __init__(self):
        self.min_font_size = 12
        self.min_contrast_ratio = 4.5  # WCAG AA standard
        self.min_padding_percent = 5.0
        self.cta_overlap_threshold = 0.1
    
    def validate_design(self, 
                        image_base64: str,
                        plan: DesignPlan,
                        target_aspect_ratio: str) -> ValidationResult:
        """Run all validations on a design."""
        
        errors = []
        warnings = []
        auto_corrections = {}
        
        # Decode image
        try:
            image_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(image_data))
            W, H = img.size
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to decode image: {str(e)}"]
            )
        
        # 1. Aspect Ratio Validation
        ar_result = self._validate_aspect_ratio(W, H, target_aspect_ratio)
        if ar_result['error']:
            errors.append(ar_result['error'])
        if ar_result['warning']:
            warnings.append(ar_result['warning'])
        
        # 2. Padding Validation
        padding_result = self._validate_padding(plan.layout, W, H)
        warnings.extend(padding_result.get('warnings', []))
        
        # 3. Color Contrast Validation
        contrast_result = self._validate_contrast(
            plan.layout.headline_color,
            "#000000"  # Assume dark background for gradient
        )
        if contrast_result['warning']:
            warnings.append(contrast_result['warning'])
            auto_corrections['headline_color'] = contrast_result.get('suggested')
        
        # 4. Text Length Validation
        text_result = self._validate_text_lengths(plan.copy)
        warnings.extend(text_result.get('warnings', []))
        
        # 5. Position Conflict Validation
        position_result = self._validate_position_conflicts(plan.layout)
        errors.extend(position_result.get('errors', []))
        warnings.extend(position_result.get('warnings', []))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            auto_corrections=auto_corrections
        )
    
    def _validate_aspect_ratio(self, width: int, height: int, target: str) -> Dict[str, Any]:
        """Check if image matches target aspect ratio."""
        
        ratio_map = {
            "1:1": (1, 1),
            "4:5": (4, 5),
            "9:16": (9, 16),
            "16:9": (16, 9),
            "4:3": (4, 3),
            "3:4": (3, 4),
        }
        
        if target not in ratio_map:
            return {"error": None, "warning": f"Unknown aspect ratio: {target}"}
        
        target_w, target_h = ratio_map[target]
        actual_ratio = width / height
        target_ratio = target_w / target_h
        
        tolerance = 0.05
        if abs(actual_ratio - target_ratio) > tolerance:
            return {
                "error": None,
                "warning": f"Aspect ratio mismatch: expected {target} ({target_ratio:.2f}), got {actual_ratio:.2f}"
            }
        
        return {"error": None, "warning": None}
    
    def _validate_padding(self, layout: LayoutConfig, width: int, height: int) -> Dict[str, Any]:
        """Ensure minimum padding is maintained."""
        
        warnings = []
        min_padding_px = int(min(width, height) * (self.min_padding_percent / 100))
        
        # Check positions imply adequate padding
        edge_positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
        
        for attr in ['title_position', 'price_position', 'logo_position']:
            pos = getattr(layout, attr, 'center')
            if pos in edge_positions:
                # Edge positions need explicit padding - just warn
                warnings.append(f"Ensure adequate padding for {attr} at {pos}")
        
        return {"warnings": warnings}
    
    def _validate_contrast(self, fg_color: str, bg_color: str) -> Dict[str, Any]:
        """Check WCAG contrast ratio between colors."""
        
        def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def relative_luminance(rgb: Tuple[int, int, int]) -> float:
            def channel_luminance(c: int) -> float:
                c_norm = c / 255
                return c_norm / 12.92 if c_norm <= 0.03928 else ((c_norm + 0.055) / 1.055) ** 2.4
            
            r, g, b = rgb
            return 0.2126 * channel_luminance(r) + 0.7152 * channel_luminance(g) + 0.0722 * channel_luminance(b)
        
        try:
            fg_rgb = hex_to_rgb(fg_color)
            bg_rgb = hex_to_rgb(bg_color)
            
            l1 = relative_luminance(fg_rgb)
            l2 = relative_luminance(bg_rgb)
            
            lighter = max(l1, l2)
            darker = min(l1, l2)
            
            contrast_ratio = (lighter + 0.05) / (darker + 0.05)
            
            if contrast_ratio < self.min_contrast_ratio:
                return {
                    "warning": f"Low contrast ratio: {contrast_ratio:.2f} (minimum: {self.min_contrast_ratio})",
                    "suggested": "#ffffff" if l2 < 0.5 else "#000000"
                }
            
            return {"warning": None}
            
        except Exception:
            return {"warning": "Could not validate contrast"}
    
    def _validate_text_lengths(self, copy) -> Dict[str, Any]:
        """Validate text doesn't exceed recommended lengths."""
        
        warnings = []
        
        if len(copy.headline) > 40:
            warnings.append(f"Headline too long ({len(copy.headline)} chars): may wrap excessively")
        
        if len(copy.subtext) > 80:
            warnings.append(f"Subtext too long ({len(copy.subtext)} chars): may overflow")
        
        if len(copy.cta) > 15:
            warnings.append(f"CTA too long ({len(copy.cta)} chars): should be snappy")
        
        return {"warnings": warnings}
    
    def _validate_position_conflicts(self, layout: LayoutConfig) -> Dict[str, Any]:
        """Check for overlapping element positions."""
        
        errors = []
        warnings = []
        
        positions = [
            ('title', layout.title_position),
            ('price', layout.price_position),
            ('logo', layout.logo_position)
        ]
        
        # Check for exact conflicts
        for i, (name1, pos1) in enumerate(positions):
            for name2, pos2 in positions[i+1:]:
                if pos1 == pos2:
                    warnings.append(f"Position conflict: {name1} and {name2} both at {pos1}")
        
        # Check for adjacent conflicts (might overlap)
        def are_adjacent(p1: str, p2: str) -> bool:
            if p1 == p2:
                return True
            # Same vertical position, adjacent horizontal
            parts1 = p1.split('-')
            parts2 = p2.split('-')
            if len(parts1) == 2 and len(parts2) == 2:
                return parts1[0] == parts2[0]  # Same row
            return False
        
        for i, (name1, pos1) in enumerate(positions):
            for name2, pos2 in positions[i+1:]:
                if are_adjacent(pos1, pos2) and pos1 != pos2:
                    warnings.append(f"Adjacent elements may overlap: {name1} ({pos1}) and {name2} ({pos2})")
        
        return {"errors": errors, "warnings": warnings}
    
    def auto_correct_layout(self, layout: LayoutConfig) -> LayoutConfig:
        """Automatically fix common layout issues."""
        
        corrected = LayoutConfig(**layout.model_dump())
        
        # Fix position conflicts by redistributing
        positions_used = set()
        
        for attr in ['title_position', 'price_position', 'logo_position']:
            current = getattr(corrected, attr)
            if current in positions_used:
                # Find alternative position
                alternatives = [
                    'top-left', 'top-center', 'top-right',
                    'bottom-left', 'bottom-center', 'bottom-right'
                ]
                for alt in alternatives:
                    if alt not in positions_used:
                        setattr(corrected, attr, alt)
                        positions_used.add(alt)
                        break
            else:
                positions_used.add(current)
        
        return corrected


# Singleton
_validator = None

def get_validator() -> LayoutValidator:
    global _validator
    if _validator is None:
        _validator = LayoutValidator()
    return _validator
