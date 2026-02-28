"""Task manager that runs the full generation pipeline via orchestrator."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete

from app.config import get_settings
from app.database import AsyncSessionFactory
from app.intelligence.deduplicator import build_dedupe_key
from app.intelligence.intent_detector import IntentDetector
from app.models import GenerationJob, JobStatus, Lead
from app.normalizer.normalized_lead import normalize_to_lead_payload
from app.normalizer.standardizer import LeadStandardizer
from app.scrapers.registry import DEFAULT_SOURCES, get_scraper
from app.scoring import score_lead


def _get_provider_error_message(sources: list[str]) -> str | None:
    """Return error message if no enabled source has valid API keys."""
    settings = get_settings()
    google_places_ok = bool((settings.google_places_api_key or "").strip())
    google_search_ok = bool(
        (settings.google_custom_search_api_key or "").strip()
        and (settings.google_custom_search_engine_id or "").strip()
    )

    if "google_maps" in sources or "google_places" in sources:
        if google_places_ok:
            return None
        return (
            "Google Places API key is missing. Set GOOGLE_PLACES_API_KEY in .env. "
            "Get a key at https://console.cloud.google.com/apis/credentials"
        )

    if "google_search" in sources and not google_search_ok:
        return (
            "Google Custom Search keys missing. Set GOOGLE_CUSTOM_SEARCH_API_KEY "
            "and GOOGLE_CUSTOM_SEARCH_ENGINE_ID in .env"
        )

    if "yellow_pages" in sources:
        return None

    return "No valid data source configured. Enable google_maps, google_search, or yellow_pages"


async def run_generation_job(job_id: UUID) -> None:
    """Run the multi-source generation pipeline."""
    async with AsyncSessionFactory() as session:
        job = await session.get(GenerationJob, job_id)
        if not job:
            return
        sources = job.sources_enabled or DEFAULT_SOURCES
        if not sources:
            sources = DEFAULT_SOURCES
        query = job.query
        location = job.location
        max_results = job.max_results or 40

    provider_error = _get_provider_error_message(sources)
    if provider_error:
        async with AsyncSessionFactory() as session:
            job = await session.get(GenerationJob, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = provider_error
                job.completed_at = datetime.utcnow()
                await session.commit()
        return

    async with AsyncSessionFactory() as session:
        job = await session.get(GenerationJob, job_id)
        if not job:
            return
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        job.error_message = None
        await session.commit()

    standardizer = LeadStandardizer()
    all_raw: list[dict] = []
    seen: set[str] = set()

    try:
        for source in sources:
            scraper = get_scraper(source)
            if not scraper:
                continue
            try:
                raw_list = await scraper.scrape(
                    query=query,
                    location=location,
                    max_results=max_results,
                )
                for raw in raw_list:
                    std = standardizer.standardize(raw)
                    std["source"] = scraper.source_name
                    key = build_dedupe_key(std, scraper.source_name)
                    if key in seen:
                        continue
                    seen.add(key)
                    all_raw.append(std)
            except Exception:
                continue

        intent_detector = IntentDetector()
        lead_payloads: list[dict] = []
        for raw in all_raw:
            score = score_lead(
                rating=raw.get("rating"),
                review_count=raw.get("review_count"),
                website=raw.get("company_website"),
                phone=raw.get("company_phone"),
                address=raw.get("street") or raw.get("address"),
            )
            intent_score = intent_detector.detect(raw)
            payload = normalize_to_lead_payload(
                raw,
                source=raw.get("source", "unknown"),
                job_id=job_id,
                lead_score=score,
            )
            payload["intent_score"] = intent_score
            lead_payloads.append(Lead(**payload))

        async with AsyncSessionFactory() as session:
            await session.execute(delete(Lead).where(Lead.job_id == job_id))
            session.add_all(lead_payloads)

            job = await session.get(GenerationJob, job_id)
            if job:
                job.status = JobStatus.completed
                job.total_results = len(lead_payloads)
                job.total_final_leads = len(lead_payloads)
                job.completed_at = datetime.utcnow()
                await session.commit()

    except Exception as exc:
        async with AsyncSessionFactory() as session:
            job = await session.get(GenerationJob, job_id)
            if job:
                job.status = JobStatus.failed
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                await session.commit()
