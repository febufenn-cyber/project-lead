"""Lead enrichment service powered by Google Gemini via Vertex AI."""

import asyncio
import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# India industry context – used to ground the model in local market realities
# ---------------------------------------------------------------------------

INDIA_INDUSTRY_CONTEXT: dict[str, dict[str, Any]] = {
    "bfsi": {
        "sector": "Banking, Financial Services & Insurance",
        "ai_use_cases": [
            "Credit risk scoring & fraud detection",
            "Personalised wealth management (robo-advisory)",
            "KYC / AML document processing with OCR + NLP",
            "Customer service chatbots for regional languages",
            "Insurance claims automation & underwriting",
        ],
        "typical_buyers": ["CTO", "Chief Digital Officer", "VP Technology", "Head of Analytics", "CISO"],
        "budget_range": "₹50L – ₹10Cr annually",
    },
    "it_services": {
        "sector": "IT Services & ITES",
        "ai_use_cases": [
            "AI-augmented software testing & QA",
            "Intelligent document processing (IDP)",
            "GenAI code-assist tooling for delivery teams",
            "Predictive resource allocation & bench management",
            "Automated RFP / proposal generation",
        ],
        "typical_buyers": ["CTO", "VP Engineering", "Delivery Head", "Innovation Lead", "Pre-Sales Director"],
        "budget_range": "₹25L – ₹5Cr annually",
    },
    "pharma": {
        "sector": "Pharmaceuticals & Life Sciences",
        "ai_use_cases": [
            "Drug discovery acceleration with molecular ML",
            "Clinical trial data analysis & patient matching",
            "Pharmacovigilance signal detection",
            "Supply chain demand forecasting",
            "Regulatory document automation (FDA/CDSCO filings)",
        ],
        "typical_buyers": ["CIO", "VP R&D", "Head of Digital Transformation", "Regulatory Affairs Director", "Supply Chain VP"],
        "budget_range": "₹1Cr – ₹20Cr annually",
    },
    "manufacturing": {
        "sector": "Manufacturing & Industry 4.0",
        "ai_use_cases": [
            "Predictive maintenance for plant machinery",
            "Computer vision quality inspection on production lines",
            "AI-driven demand planning & inventory optimisation",
            "Energy consumption analytics & optimisation",
            "Automated procurement & vendor risk scoring",
        ],
        "typical_buyers": ["Plant Head", "CTO", "Head of Operations", "VP Supply Chain", "Chief Digital Officer"],
        "budget_range": "₹30L – ₹8Cr annually",
    },
    "ecommerce": {
        "sector": "E-Commerce & D2C Retail",
        "ai_use_cases": [
            "Personalised product recommendation engines",
            "Dynamic pricing & markdown optimisation",
            "AI-powered customer support (multilingual bots)",
            "Visual search & try-on features",
            "Return fraud detection & prevention",
        ],
        "typical_buyers": ["CTO", "VP Product", "Head of Growth", "Chief Data Officer", "VP Customer Experience"],
        "budget_range": "₹20L – ₹5Cr annually",
    },
    "government": {
        "sector": "Government & Public Sector",
        "ai_use_cases": [
            "Citizen grievance NLP classification & routing",
            "Aadhaar / DigiLocker AI document verification",
            "Tax evasion pattern detection",
            "Smart city traffic & utilities management",
            "AI-assisted policy impact modelling",
        ],
        "typical_buyers": ["IT Secretary", "NIC Project Director", "DG (Digital Services)", "Mission Director", "Joint Secretary (IT)"],
        "budget_range": "₹50L – ₹50Cr (tender-based)",
    },
    "telecom": {
        "sector": "Telecommunications",
        "ai_use_cases": [
            "Network anomaly detection & self-healing",
            "Churn prediction & proactive retention",
            "AI-driven 5G network slice optimisation",
            "Personalised tariff plan recommendation",
            "Call-centre AI + voice bot automation",
        ],
        "typical_buyers": ["CTO", "Chief Network Officer", "VP Customer Experience", "Head of AI/ML", "VP Revenue Assurance"],
        "budget_range": "₹1Cr – ₹25Cr annually",
    },
    "startups": {
        "sector": "Tech Startups & New-Age Companies",
        "ai_use_cases": [
            "AI-native product feature development",
            "LLM-based customer onboarding automation",
            "Growth analytics & funnel optimisation with ML",
            "Automated compliance & legal document review",
            "Investor-ready data room intelligence",
        ],
        "typical_buyers": ["Founder / CEO", "CTO", "Head of Product", "VP Engineering", "Chief AI Officer"],
        "budget_range": "₹5L – ₹2Cr annually",
    },
}

# ---------------------------------------------------------------------------
# Token & cost helpers
# ---------------------------------------------------------------------------

# Approximate Gemini 2.5 Pro pricing (USD per 1M tokens, as of Q1 2026)
_GEMINI_INPUT_PRICE_PER_1M = 1.25
_GEMINI_OUTPUT_PRICE_PER_1M = 5.00
_USD_TO_INR = 84.0  # approximate exchange rate

# Estimated tokens per lead enrichment call
_AVG_INPUT_TOKENS = 800
_AVG_OUTPUT_TOKENS = 600


def estimate_enrichment_cost(lead_count: int) -> dict[str, Any]:
    """Return approximate cost for enriching *lead_count* leads."""
    total_input = _AVG_INPUT_TOKENS * lead_count
    total_output = _AVG_OUTPUT_TOKENS * lead_count
    cost_usd = (
        (total_input / 1_000_000) * _GEMINI_INPUT_PRICE_PER_1M
        + (total_output / 1_000_000) * _GEMINI_OUTPUT_PRICE_PER_1M
    )
    cost_inr = cost_usd * _USD_TO_INR
    return {
        "lead_count": lead_count,
        "estimated_input_tokens": total_input,
        "estimated_output_tokens": total_output,
        "estimated_cost_usd": round(cost_usd, 4),
        "estimated_cost_inr": round(cost_inr, 2),
        "model": settings.vertex_model,
        "note": "Estimates based on average token usage; actual costs may vary.",
    }


# ---------------------------------------------------------------------------
# Vertex AI authentication helper
# ---------------------------------------------------------------------------

async def _get_vertex_access_token() -> str:
    """Return a fresh GCP access token using Application Default Credentials."""

    def _refresh_sync() -> str:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        return credentials.token  # type: ignore[return-value]

    return await asyncio.to_thread(_refresh_sync)


# ---------------------------------------------------------------------------
# Core enrichment service
# ---------------------------------------------------------------------------

def _build_enrichment_prompt(lead: dict[str, Any], industry_hint: str | None) -> str:
    sector_context = ""
    if industry_hint and industry_hint.lower() in INDIA_INDUSTRY_CONTEXT:
        ctx = INDIA_INDUSTRY_CONTEXT[industry_hint.lower()]
        sector_context = (
            f"\nIndustry context for {ctx['sector']}:\n"
            f"- Common AI use cases: {', '.join(ctx['ai_use_cases'][:3])}\n"
            f"- Typical decision-makers: {', '.join(ctx['typical_buyers'][:3])}\n"
            f"- Typical budget range: {ctx['budget_range']}\n"
        )

    return f"""You are an expert B2B sales intelligence analyst specialising in the INDIAN enterprise market.
Analyse the following business lead and return a JSON object with your findings.
{sector_context}
LEAD DATA:
- Company: {lead.get('company_name') or lead.get('business_name', 'Unknown')}
- Website: {lead.get('company_website') or lead.get('website', 'Not provided')}
- City: {lead.get('city', 'Unknown')}, State: {lead.get('state', 'Unknown')}, Country: {lead.get('country', 'India')}
- Phone: {lead.get('company_phone') or lead.get('phone', 'Not provided')}
- Industry hint: {industry_hint or 'Not specified'}
- Rating: {lead.get('rating', 'N/A')}, Reviews: {lead.get('review_count', 0)}

Return ONLY a valid JSON object with these exact keys:
{{
  "company_summary": "2-3 sentence summary of the company and its likely AI needs",
  "estimated_size": "micro|small|medium|large|enterprise",
  "estimated_employee_count": "1-10|11-50|51-200|201-500|500+",
  "ai_adoption_readiness": "low|medium|high",
  "ai_readiness_reasoning": "1-2 sentences explaining readiness assessment",
  "pain_points": ["pain1", "pain2", "pain3", "pain4", "pain5"],
  "recommended_approach": "Specific outreach strategy for Indian market context",
  "industry_vertical": "Primary industry classification",
  "decision_maker_titles": ["title1", "title2", "title3"],
  "urgency_score": 7,
  "talking_points": ["point1", "point2", "point3"],
  "competitive_landscape": "Brief note on competition and positioning"
}}

Focus on Indian market dynamics: price sensitivity, local language preference,
regulatory environment (RBI, SEBI, DPDP Act), and digital-India alignment.
Return only the JSON object — no markdown fences, no extra text."""


async def enrich_lead(
    lead: dict[str, Any],
    industry_hint: str | None = None,
) -> dict[str, Any]:
    """Enrich a single lead dict via Gemini on Vertex AI.

    Returns the enrichment dict on success, or a minimal error dict on failure.
    """
    if not settings.vertex_project_id:
        logger.warning("VERTEX_PROJECT_ID not configured; returning empty enrichment")
        return {"error": "Vertex AI not configured", "ai_adoption_readiness": "low", "urgency_score": 1}

    prompt = _build_enrichment_prompt(lead, industry_hint)
    endpoint = (
        f"https://{settings.vertex_location}-aiplatform.googleapis.com/v1"
        f"/projects/{settings.vertex_project_id}"
        f"/locations/{settings.vertex_location}"
        f"/publishers/google/models/{settings.vertex_model}:generateContent"
    )

    try:
        token = await _get_vertex_access_token()
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1024,
            },
        }
        async with httpx.AsyncClient(timeout=settings.enrichment_timeout) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return _parse_json_response(raw_text)

    except httpx.HTTPStatusError as exc:
        logger.error("Vertex AI HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
    except Exception as exc:
        logger.error("Vertex AI enrichment failed: %s", exc)

    return {"error": "enrichment_failed", "ai_adoption_readiness": "low", "urgency_score": 1}


def _parse_json_response(text: str) -> dict[str, Any]:
    """Extract a JSON object from the model's text output."""
    # Strip markdown code fences if present
    if "```" in text:
        text = text.split("```")[-2] if text.count("```") >= 2 else text.replace("```", "")
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt to locate the first {...} block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse enrichment JSON; returning fallback")
    return {
        "company_summary": "Analysis unavailable",
        "ai_adoption_readiness": "low",
        "urgency_score": 1,
        "pain_points": [],
        "talking_points": [],
        "decision_maker_titles": [],
        "error": "json_parse_failed",
    }


async def batch_enrich_leads(
    leads: list[dict[str, Any]],
    industry_hint: str | None = None,
    concurrency: int = 3,
) -> list[dict[str, Any]]:
    """Enrich multiple leads with bounded concurrency.

    Returns a list of enrichment dicts in the same order as *leads*.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(lead: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await enrich_lead(lead, industry_hint)

    return await asyncio.gather(*[_bounded(lead) for lead in leads])
