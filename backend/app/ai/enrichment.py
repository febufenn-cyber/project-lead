"""AI-powered lead enrichment service."""

import json
import logging
from typing import Any, Optional
from datetime import timedelta

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class AIEnrichmentService:
    """Service for enriching lead data using AI models."""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_ttl = timedelta(hours=24)  # Cache AI responses for 24 hours
        
    async def enrich_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        """
        Enrich a lead with AI-powered insights.
        
        Args:
            lead: Lead dictionary with fields like business_name, website, etc.
            
        Returns:
            Dictionary with enrichment data.
        """
        # Check cache first (implement Redis caching later)
        cache_key = self._generate_cache_key(lead)
        # TODO: Implement Redis cache lookup
        
        # Try OpenAI first, then fallback to local Ollama, then mock data
        enrichment = await self._enrich_with_openai(lead)
        if enrichment:
            # TODO: Cache the result
            return enrichment
            
        # Fallback to local Ollama
        enrichment = await self._enrich_with_ollama(lead)
        if enrichment:
            return enrichment
            
        # Final fallback: mock data (for development)
        return self._generate_mock_enrichment(lead)
    
    async def _enrich_with_openai(self, lead: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Enrich using OpenAI GPT models."""
        if not self.settings.openai_api_key:
            logger.debug("OpenAI API key not configured")
            return None
            
        prompt = self._build_enrichment_prompt(lead)
        
        try:
            # Use OpenAI API
            # Note: We'll implement this properly once we have the API key
            # For now, return None to trigger fallback
            return None
        except Exception as e:
            logger.error(f"OpenAI enrichment failed: {e}")
            return None
    
    async def _enrich_with_ollama(self, lead: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Enrich using local Ollama model."""
        if not self.settings.ollama_base_url:
            logger.debug("Ollama base URL not configured")
            return None
            
        prompt = self._build_enrichment_prompt(lead)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/generate",
                    json={
                        "model": self.settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3}
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                # Parse the response
                text = result.get("response", "").strip()
                return self._parse_enrichment_response(text)
                
        except Exception as e:
            logger.error(f"Ollama enrichment failed: {e}")
            return None
    
    def _generate_mock_enrichment(self, lead: dict[str, Any]) -> dict[str, Any]:
        """Generate mock enrichment data for development."""
        business_name = lead.get("business_name", "").lower()
        
        # Simple heuristics based on business name keywords
        if any(word in business_name for word in ["restaurant", "cafe", "diner", "bistro"]):
            industry = "Restaurant & Food Services"
            size_range = "1-10"
            revenue_range = "0-1M"
            pain_points = ["High employee turnover", "Seasonal fluctuations", "Food cost management"]
        elif any(word in business_name for word in ["tech", "software", "app", "digital"]):
            industry = "Technology & Software"
            size_range = "11-50"
            revenue_range = "1M-5M"
            pain_points = ["Talent acquisition", "Product-market fit", "Technical debt"]
        elif any(word in business_name for word in ["consulting", "advisory", "agency"]):
            industry = "Professional Services"
            size_range = "1-10"
            revenue_range = "0-1M"
            pain_points = ["Client acquisition", "Project pricing", "Service differentiation"]
        else:
            industry = "General Business"
            size_range = "1-10"
            revenue_range = "0-1M"
            pain_points = ["Marketing reach", "Customer retention", "Operational efficiency"]
        
        return {
            "company_size": size_range,
            "revenue_range": revenue_range,
            "industry": industry,
            "pain_points": pain_points,
            "confidence": 0.6,
            "source": "mock_heuristics",
            "enrichment_date": "2026-02-28"
        }
    
    def _build_enrichment_prompt(self, lead: dict[str, Any]) -> str:
        """Build a prompt for AI enrichment."""
        return f"""
        Analyze this business lead and provide structured enrichment:
        
        Company: {lead.get('business_name', 'Unknown')}
        Website: {lead.get('website', 'Not provided')}
        Location: {lead.get('city', 'Unknown')}, {lead.get('state', 'Unknown')}
        Industry hints: {lead.get('category', 'Not specified')}
        Rating: {lead.get('rating', 'Not rated')}
        Review count: {lead.get('review_count', 0)}
        
        Please provide the following information in JSON format:
        {{
            "company_size": "1-10|11-50|51-200|201-500|501-1000|1000+",
            "revenue_range": "0-1M|1M-5M|5M-10M|10M-50M|50M+",
            "industry": "Primary industry classification",
            "pain_points": ["list", "of", "3-5", "likely pain points"],
            "confidence": 0.0-1.0,
            "outreach_angle": "Personalized outreach suggestion"
        }}
        
        Base your analysis on:
        1. Industry benchmarks
        2. Location factors
        3. Online presence indicators
        4. Review count and rating
        5. Common business challenges
        
        Return only valid JSON.
        """
    
    def _parse_enrichment_response(self, text: str) -> dict[str, Any]:
        """Parse AI response text into structured data."""
        try:
            # Try to extract JSON from the response
            lines = text.strip().split('\n')
            json_start = -1
            json_end = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                if line.strip().endswith('}'):
                    json_end = i
                    break
            
            if json_start >= 0 and json_end >= 0:
                json_text = '\n'.join(lines[json_start:json_end + 1])
                data = json.loads(json_text)
                
                # Ensure required fields
                defaults = {
                    "company_size": "1-10",
                    "revenue_range": "0-1M",
                    "industry": "Unknown",
                    "pain_points": [],
                    "confidence": 0.7,
                    "outreach_angle": "Consider reaching out to discuss business challenges",
                    "source": "ai_enrichment"
                }
                
                for key, default in defaults.items():
                    if key not in data:
                        data[key] = default
                
                return data
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
        
        # Return default structure if parsing fails
        return {
            "company_size": "1-10",
            "revenue_range": "0-1M",
            "industry": "Unknown",
            "pain_points": [],
            "confidence": 0.5,
            "outreach_angle": "Consider reaching out to discuss business challenges",
            "source": "ai_enrichment_parsing_failed"
        }
    
    def _generate_cache_key(self, lead: dict[str, Any]) -> str:
        """Generate a cache key for the lead."""
        business_name = lead.get("business_name", "").lower().replace(" ", "_")
        location = f"{lead.get('city', '')}_{lead.get('state', '')}".lower().replace(" ", "_")
        return f"enrichment:{business_name}:{location}"


# Singleton instance
enrichment_service = AIEnrichmentService()