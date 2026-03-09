"""AI-powered outreach email generator using Gemini via Vertex AI."""

import asyncio
import json
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.services.claude_enrichment import _get_vertex_access_token, _parse_json_response

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_outreach_prompt(
    lead: dict[str, Any],
    sender_name: str,
    sender_title: str,
    tone: str,
    language: str,
) -> str:
    company = lead.get("company_name") or lead.get("business_name", "your company")
    city = lead.get("city", "India")
    enrichment = lead.get("ai_enrichment") or {}
    pain_points = enrichment.get("pain_points", [])
    talking_points = enrichment.get("talking_points", [])
    readiness = enrichment.get("ai_adoption_readiness", "medium")
    decision_makers = enrichment.get("decision_maker_titles", ["Decision Maker"])

    language_instruction = (
        "Write in a natural Hinglish mix (English sentences with common Hindi phrases like "
        "'Aapke liye', 'Bilkul', 'Dhanyavaad', etc.) that feels authentic to Indian B2B communication."
        if language == "hindi_english"
        else "Write in clear, professional Indian English."
    )

    tone_map = {
        "formal": "highly professional and formal",
        "conversational": "warm, conversational yet professional",
        "consultative": "consultative and insight-led",
    }
    tone_desc = tone_map.get(tone, "professional")

    return f"""You are an expert B2B sales copywriter specialising in the Indian enterprise market.
Generate personalised outreach copy for the following lead. {language_instruction}
Tone: {tone_desc}.

LEAD CONTEXT:
- Company: {company}, City: {city}
- AI readiness: {readiness}
- Pain points: {', '.join(pain_points[:3]) if pain_points else 'Not identified'}
- Key talking points: {', '.join(talking_points[:2]) if talking_points else 'AI transformation'}
- Primary decision-maker titles: {', '.join(decision_makers[:2]) if decision_makers else 'Leadership'}

SENDER:
- Name: {sender_name}
- Title: {sender_title}

Return ONLY a valid JSON object with these exact keys:
{{
  "subject": "Email subject line (max 60 chars)",
  "body": "Initial email body (max 150 words, no placeholders like [NAME])",
  "followup_subject": "Follow-up email subject line",
  "followup_body": "Follow-up email body (max 100 words)",
  "linkedin_message": "LinkedIn connection request message (max 300 characters)",
  "key_personalization": "One sentence explaining what makes this outreach personalised"
}}

Rules:
- Reference the company name naturally
- Mention a specific Indian market insight or regulatory context where relevant
- End emails with a soft, low-friction CTA (e.g., a 20-minute call)
- No generic filler phrases like 'I hope this email finds you well'
Return only the JSON object."""


async def generate_outreach(
    lead: dict[str, Any],
    sender_name: str = "Sales Team",
    sender_title: str = "Business Development Manager",
    tone: str = "consultative",
    language: str = "english",
) -> dict[str, Any]:
    """Generate personalised outreach copy for a single enriched lead."""
    if not settings.vertex_project_id:
        logger.warning("VERTEX_PROJECT_ID not configured; returning placeholder outreach")
        return _placeholder_outreach(lead)

    prompt = _build_outreach_prompt(lead, sender_name, sender_title, tone, language)
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
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
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
        logger.error("Vertex AI outreach HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
    except Exception as exc:
        logger.error("Vertex AI outreach generation failed: %s", exc)

    return _placeholder_outreach(lead)


def _placeholder_outreach(lead: dict[str, Any]) -> dict[str, Any]:
    company = lead.get("company_name") or lead.get("business_name", "your organisation")
    return {
        "subject": f"AI transformation opportunity for {company}",
        "body": (
            f"Hi,\n\nI came across {company} and wanted to connect regarding how AI can help "
            "streamline your operations and accelerate growth in the Indian market.\n\n"
            "Would you be open to a quick 20-minute call to explore this?\n\nBest regards"
        ),
        "followup_subject": f"Following up — AI for {company}",
        "followup_body": (
            "Just following up on my previous note. Many Indian enterprises are already seeing "
            "strong ROI from targeted AI adoption. Happy to share a relevant case study.\n\nBest regards"
        ),
        "linkedin_message": (
            f"Hi, I noticed {company}'s work and wanted to connect. "
            "I help Indian enterprises adopt AI practically — happy to share insights."
        ),
        "key_personalization": "Outreach generated using placeholder (AI service not configured).",
        "error": "vertex_ai_not_configured",
    }


async def bulk_generate_outreach(
    leads: list[dict[str, Any]],
    sender_name: str = "Sales Team",
    sender_title: str = "Business Development Manager",
    tone: str = "consultative",
    language: str = "english",
    concurrency: int = 3,
) -> list[dict[str, Any]]:
    """Generate outreach copy for multiple leads with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(lead: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await generate_outreach(lead, sender_name, sender_title, tone, language)

    return await asyncio.gather(*[_bounded(lead) for lead in leads])
