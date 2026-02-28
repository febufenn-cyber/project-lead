"""AI-powered lead scoring service."""

import json
import logging
from typing import Any, Optional

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class AIScoringService:
    """Service for AI-powered lead scoring and conversion prediction."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def predict_conversion_probability(self, lead: dict[str, Any]) -> dict[str, Any]:
        """
        Predict conversion probability using AI.
        
        Args:
            lead: Lead dictionary with fields.
            
        Returns:
            Dictionary with probability, confidence, and key factors.
        """
        # Extract features for scoring
        features = self._extract_features(lead)
        
        # Try OpenAI first, then Ollama, then fallback to rule-based
        prediction = await self._predict_with_openai(features, lead)
        if prediction:
            return prediction
            
        prediction = await self._predict_with_ollama(features, lead)
        if prediction:
            return prediction
            
        # Fallback to rule-based scoring
        return self._rule_based_prediction(features)
    
    def _extract_features(self, lead: dict[str, Any]) -> dict[str, Any]:
        """Extract numeric and categorical features for scoring."""
        rating = lead.get("rating", 0)
        review_count = lead.get("review_count", 0)
        website = lead.get("website")
        phone = lead.get("phone")
        address = lead.get("address")
        email = lead.get("email")
        
        # Calculate feature scores
        features = {
            "rating_normalized": max(0.0, min(5.0, float(rating))) / 5.0,
            "review_count_log": max(0.0, min(1.0, (review_count ** 0.3) / 10.0)),
            "has_website": 1.0 if website else 0.0,
            "has_phone": 1.0 if phone else 0.0,
            "has_address": 1.0 if address else 0.0,
            "has_email": 1.0 if email else 0.0,
            "high_review_count": 1.0 if review_count >= 50 else 0.0,
            "high_rating": 1.0 if rating >= 4.0 else 0.0,
        }
        
        # Add enrichment features if available
        if "ai_enrichment" in lead and isinstance(lead["ai_enrichment"], dict):
            enrichment = lead["ai_enrichment"]
            features["company_size_score"] = self._size_to_score(enrichment.get("company_size"))
            features["revenue_score"] = self._revenue_to_score(enrichment.get("revenue_range"))
        
        return features
    
    def _size_to_score(self, size_range: Optional[str]) -> float:
        """Convert company size range to numeric score (0-1)."""
        if not size_range:
            return 0.5
            
        mapping = {
            "1-10": 0.3,
            "11-50": 0.5,
            "51-200": 0.7,
            "201-500": 0.8,
            "501-1000": 0.9,
            "1000+": 1.0
        }
        return mapping.get(size_range, 0.5)
    
    def _revenue_to_score(self, revenue_range: Optional[str]) -> float:
        """Convert revenue range to numeric score (0-1)."""
        if not revenue_range:
            return 0.5
            
        mapping = {
            "0-1M": 0.3,
            "1M-5M": 0.5,
            "5M-10M": 0.7,
            "10M-50M": 0.8,
            "50M+": 1.0
        }
        return mapping.get(revenue_range, 0.5)
    
    async def _predict_with_openai(self, features: dict[str, Any], lead: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Predict using OpenAI GPT models."""
        if not self.settings.openai_api_key:
            return None
            
        prompt = self._build_prediction_prompt(features, lead)
        
        # TODO: Implement OpenAI API call
        # For now, return None to trigger fallback
        return None
    
    async def _predict_with_ollama(self, features: dict[str, Any], lead: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Predict using local Ollama model."""
        if not self.settings.ollama_base_url:
            return None
            
        prompt = self._build_prediction_prompt(features, lead)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/generate",
                    json={
                        "model": self.settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.2}
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                text = result.get("response", "").strip()
                return self._parse_prediction_response(text)
                
        except Exception as e:
            logger.error(f"Ollama prediction failed: {e}")
            return None
    
    def _rule_based_prediction(self, features: dict[str, Any]) -> dict[str, Any]:
        """Fallback rule-based prediction."""
        # Weighted sum of features
        weights = {
            "rating_normalized": 0.25,
            "review_count_log": 0.20,
            "has_website": 0.15,
            "has_phone": 0.10,
            "has_address": 0.10,
            "has_email": 0.10,
            "high_review_count": 0.05,
            "high_rating": 0.05,
        }
        
        # Add enrichment weights if available
        if "company_size_score" in features:
            weights["company_size_score"] = 0.05
        if "revenue_score" in features:
            weights["revenue_score"] = 0.05
        
        # Calculate weighted score
        total_weight = sum(weights.values())
        weighted_sum = sum(features.get(key, 0) * weight for key, weight in weights.items())
        probability = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # Determine key factors
        key_factors = []
        for key, weight in weights.items():
            if features.get(key, 0) > 0.7 and weight >= 0.1:
                factor_name = key.replace("_", " ").title()
                key_factors.append(factor_name)
        
        return {
            "probability": round(probability, 3),
            "confidence": 0.7,
            "key_factors": key_factors[:3],  # Top 3 factors
            "model": "rule_based_fallback",
            "features_used": list(weights.keys())
        }
    
    def _build_prediction_prompt(self, features: dict[str, Any], lead: dict[str, Any]) -> str:
        """Build a prompt for conversion prediction."""
        return f"""
        Predict conversion probability (0-100%) for this business lead:
        
        Company: {lead.get('business_name', 'Unknown')}
        Industry: {lead.get('category', 'Not specified')}
        Location: {lead.get('city', 'Unknown')}, {lead.get('state', 'Unknown')}
        Rating: {lead.get('rating', 'Not rated')}
        Reviews: {lead.get('review_count', 0)}
        Website: {'Yes' if lead.get('website') else 'No'}
        Contact Info: {'Phone' if lead.get('phone') else ''} {'Email' if lead.get('email') else ''}
        
        Features:
        {json.dumps(features, indent=2)}
        
        Consider:
        1. Online presence strength
        2. Review sentiment and volume
        3. Contact information completeness
        4. Industry trends
        5. Company stability indicators
        
        Return JSON with:
        {{
            "probability": 0.85,  # 0-1
            "confidence": 0.92,   # 0-1
            "key_factors": ["list", "of", "top", "3-5", "factors"],
            "recommended_action": "immediate_followup|schedule_call|nurture|discard"
        }}
        
        Return only valid JSON.
        """
    
    def _parse_prediction_response(self, text: str) -> dict[str, Any]:
        """Parse AI prediction response."""
        try:
            # Extract JSON
            lines = text.strip().split('\n')
            json_text = ""
            in_json = False
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('{'):
                    in_json = True
                if in_json:
                    json_text += line + '\n'
                if stripped.endswith('}'):
                    break
            
            if json_text:
                data = json.loads(json_text)
                
                # Validate and add defaults
                probability = data.get("probability", 0.5)
                if isinstance(probability, (int, float)):
                    probability = max(0.0, min(1.0, float(probability)))
                else:
                    probability = 0.5
                
                defaults = {
                    "probability": probability,
                    "confidence": data.get("confidence", 0.7),
                    "key_factors": data.get("key_factors", []),
                    "recommended_action": data.get("recommended_action", "nurture"),
                    "model": "ai_prediction"
                }
                
                result = {}
                for key, default in defaults.items():
                    result[key] = data.get(key, default)
                
                return result
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse prediction response: {e}")
        
        # Return fallback
        return self._rule_based_prediction({})


# Singleton instance
scoring_service = AIScoringService()