"""
Active Learning Selector - Intelligently selects samples for training
"""
from typing import List, Dict, Any, Optional
from collections import Counter
import random

from ..models.schemas import DatasetSample, EvaluationScores
from ..models.database import get_dataset_db


class ActiveLearningSelector:
    """Selects training samples based on active learning principles."""
    
    def __init__(self):
        self.low_score_weight = 0.4
        self.low_frequency_weight = 0.3
        self.approved_weight = 0.3
    
    def select_for_training(self,
                            target_count: int = 100,
                            tenant_id: Optional[str] = None,
                            include_approved: bool = True,
                            include_low_scores: bool = True,
                            include_rare_categories: bool = True) -> List[DatasetSample]:
        """
        Select samples for training using active learning strategy.
        
        Strategy:
        1. Prioritize low-scoring samples (model struggles → needs training)
        2. Prioritize low-frequency styles/platforms (underrepresented)
        3. Include positively approved feedback (user-validated quality)
        """
        
        db = get_dataset_db()
        all_samples = db.get_all_samples(tenant_id=tenant_id, limit=5000)
        
        if not all_samples:
            return []
        
        selected = []
        
        # Calculate distribution frequencies
        category_counts = Counter(s.category for s in all_samples)
        platform_counts = Counter(s.platform for s in all_samples)
        style_counts = Counter(s.style for s in all_samples)
        
        # Score each sample
        scored_samples = []
        for sample in all_samples:
            score = self._calculate_priority_score(
                sample,
                category_counts,
                platform_counts,
                style_counts,
                include_approved,
                include_low_scores,
                include_rare_categories
            )
            scored_samples.append((score, sample))
        
        # Sort by priority (higher = more valuable for training)
        scored_samples.sort(key=lambda x: x[0], reverse=True)
        
        # Select top samples
        for score, sample in scored_samples[:target_count]:
            selected.append(sample)
        
        return selected
    
    def _calculate_priority_score(self,
                                   sample: DatasetSample,
                                   category_counts: Counter,
                                   platform_counts: Counter,
                                   style_counts: Counter,
                                   include_approved: bool,
                                   include_low_scores: bool,
                                   include_rare_categories: bool) -> float:
        """Calculate training priority score for a sample."""
        
        score = 0.0
        
        # 1. Low AI score = high training priority (model needs improvement here)
        if include_low_scores and sample.evaluation_scores:
            avg_eval = sample.evaluation_scores.average if hasattr(sample.evaluation_scores, 'average') else 5.0
            # Invert: lower eval score → higher training priority
            score += (10 - avg_eval) * self.low_score_weight
        
        # 2. Low frequency = high priority (underrepresented data)
        if include_rare_categories:
            total = sum(category_counts.values())
            cat_freq = category_counts.get(sample.category, 0) / max(total, 1)
            plat_freq = platform_counts.get(sample.platform, 0) / max(total, 1)
            style_freq = style_counts.get(sample.style, 0) / max(total, 1)
            
            # Invert: lower frequency → higher priority
            avg_freq = (cat_freq + plat_freq + style_freq) / 3
            score += (1 - avg_freq) * 10 * self.low_frequency_weight
        
        # 3. User-approved = confirmed quality
        if include_approved and sample.feedback:
            if sample.feedback.get('feedback_type') == 'approve':
                score += 10 * self.approved_weight
                # Boost for high user rating
                rating = sample.feedback.get('rating', 3)
                score += (rating - 3) * 0.5
            elif sample.feedback.get('feedback_type') == 'reject':
                # Rejected samples are also valuable for learning what NOT to do
                score += 5 * self.approved_weight
        
        # 4. Bonus for samples with corrections (explicit guidance)
        if sample.feedback and sample.feedback.get('corrections'):
            score += 2
        
        return score
    
    def get_underrepresented_categories(self, 
                                         threshold_percent: float = 10.0,
                                         tenant_id: Optional[str] = None) -> Dict[str, List[str]]:
        """Identify underrepresented categories/platforms/styles."""
        
        db = get_dataset_db()
        all_samples = db.get_all_samples(tenant_id=tenant_id, limit=5000)
        
        if not all_samples:
            return {"categories": [], "platforms": [], "styles": []}
        
        total = len(all_samples)
        threshold = total * (threshold_percent / 100)
        
        category_counts = Counter(s.category for s in all_samples)
        platform_counts = Counter(s.platform for s in all_samples)
        style_counts = Counter(s.style for s in all_samples)
        
        underrepresented = {
            "categories": [k for k, v in category_counts.items() if v < threshold],
            "platforms": [k for k, v in platform_counts.items() if v < threshold],
            "styles": [k for k, v in style_counts.items() if v < threshold]
        }
        
        return underrepresented
    
    def suggest_next_generation_params(self, tenant_id: Optional[str] = None) -> Dict[str, str]:
        """Suggest parameters for next generation to balance dataset."""
        
        underrep = self.get_underrepresented_categories(tenant_id=tenant_id)
        
        suggestions = {}
        
        if underrep['categories']:
            suggestions['category'] = random.choice(underrep['categories'])
        
        if underrep['platforms']:
            suggestions['platform'] = random.choice(underrep['platforms'])
        
        if underrep['styles']:
            suggestions['style'] = random.choice(underrep['styles'])
        
        return suggestions
    
    def calculate_dataset_balance_score(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate how balanced the current dataset is."""
        
        db = get_dataset_db()
        all_samples = db.get_all_samples(tenant_id=tenant_id, limit=5000)
        
        if not all_samples:
            return {"balance_score": 0, "recommendations": ["No data yet"]}
        
        category_counts = Counter(s.category for s in all_samples)
        platform_counts = Counter(s.platform for s in all_samples)
        style_counts = Counter(s.style for s in all_samples)
        
        def gini_coefficient(counts: Counter) -> float:
            """Calculate Gini coefficient (0 = perfect equality, 1 = max inequality)."""
            values = sorted(counts.values())
            n = len(values)
            if n == 0:
                return 0
            cumsum = 0
            for i, v in enumerate(values):
                cumsum += (2 * (i + 1) - n - 1) * v
            return cumsum / (n * sum(values)) if sum(values) > 0 else 0
        
        cat_gini = gini_coefficient(category_counts)
        plat_gini = gini_coefficient(platform_counts)
        style_gini = gini_coefficient(style_counts)
        
        avg_gini = (cat_gini + plat_gini + style_gini) / 3
        balance_score = round((1 - avg_gini) * 100, 1)
        
        recommendations = []
        if cat_gini > 0.3:
            rarest = category_counts.most_common()[-1][0] if category_counts else None
            if rarest:
                recommendations.append(f"Generate more '{rarest}' category samples")
        
        if plat_gini > 0.3:
            rarest = platform_counts.most_common()[-1][0] if platform_counts else None
            if rarest:
                recommendations.append(f"Generate more '{rarest}' platform samples")
        
        if style_gini > 0.3:
            rarest = style_counts.most_common()[-1][0] if style_counts else None
            if rarest:
                recommendations.append(f"Generate more '{rarest}' style samples")
        
        return {
            "balance_score": balance_score,
            "category_gini": round(cat_gini, 3),
            "platform_gini": round(plat_gini, 3),
            "style_gini": round(style_gini, 3),
            "recommendations": recommendations or ["Dataset is well balanced!"]
        }


# Singleton
_selector = None

def get_selector() -> ActiveLearningSelector:
    global _selector
    if _selector is None:
        _selector = ActiveLearningSelector()
    return _selector
