"""Email finder and verification API."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.database import AsyncSessionFactory
from app.email_finder.finder_engine import EmailFinderEngine
from app.email_finder.verifier import EmailVerifier
from app.models import Lead

router = APIRouter(prefix="/email", tags=["email"])


class VerifyRequest(BaseModel):
    email: str = Field(min_length=3)


class VerifyResponse(BaseModel):
    email: str
    status: str
    reason: str | None
    confidence: int
    is_disposable: bool = False
    is_free_provider: bool = False
    mx_valid: bool = False


class BulkVerifyRequest(BaseModel):
    emails: list[str] = Field(max_length=100)


class BulkVerifyResponse(BaseModel):
    results: list[VerifyResponse]
    total: int


class FindEmailsRequest(BaseModel):
    domain: str = Field(min_length=2)
    first_name: str | None = None
    last_name: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class EmailCandidateResponse(BaseModel):
    email: str
    confidence: int
    source: str
    first_name: str | None
    last_name: str | None
    position: str | None


class FindEmailsResponse(BaseModel):
    candidates: list[EmailCandidateResponse]


@router.post("/verify", response_model=VerifyResponse)
async def verify_email(req: VerifyRequest) -> VerifyResponse:
    verifier = EmailVerifier()
    result = await verifier.verify(req.email)
    return VerifyResponse(
        email=req.email,
        status=result.status,
        reason=result.reason,
        confidence=result.confidence,
        is_disposable=result.is_disposable,
        is_free_provider=result.is_free_provider,
        mx_valid=result.mx_valid,
    )


@router.post("/verify/bulk", response_model=BulkVerifyResponse)
async def bulk_verify(req: BulkVerifyRequest) -> BulkVerifyResponse:
    verifier = EmailVerifier()
    results = []
    for email in req.emails:
        r = await verifier.verify(email)
        results.append(
            VerifyResponse(
                email=email,
                status=r.status,
                reason=r.reason,
                confidence=r.confidence,
                is_disposable=r.is_disposable,
                is_free_provider=r.is_free_provider,
                mx_valid=r.mx_valid,
            )
        )
    return BulkVerifyResponse(results=results, total=len(results))


@router.post("/find", response_model=FindEmailsResponse)
async def find_emails(req: FindEmailsRequest) -> FindEmailsResponse:
    engine = EmailFinderEngine()
    candidates = await engine.find_emails(
        domain=req.domain,
        first_name=req.first_name,
        last_name=req.last_name,
        limit=req.limit,
    )
    return FindEmailsResponse(
        candidates=[
            EmailCandidateResponse(
                email=c.email,
                confidence=c.confidence,
                source=c.source,
                first_name=c.first_name,
                last_name=c.last_name,
                position=c.position,
            )
            for c in candidates
        ]
    )


async def _enrich_lead_emails(lead_id: UUID) -> None:
    """Background task: find/verify email and company enrichment for a lead."""
    from app.enrichment.company_enricher import CompanyEnricher

    engine = EmailFinderEngine()
    verifier = EmailVerifier()
    company_enricher = CompanyEnricher()

    async with AsyncSessionFactory() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            return
        domain = lead.company_domain or (
            lead.company_website.split("//")[-1].split("/")[0].replace("www.", "")
            if lead.company_website else None
        )
        if not domain:
            return

        company_data = {
            "company_name": lead.company_name,
            "company_domain": domain,
            "company_website": lead.company_website,
        }
        enriched_company = await company_enricher.enrich(company_data)
        if enriched_company.get("raw_data"):
            lead.raw_data = dict(lead.raw_data or {})
            lead.raw_data.update(enriched_company.get("raw_data", {}))
        lead.is_enriched = True

        first = lead.contact_first_name or ""
        last = lead.contact_last_name or ""
        candidates = await engine.find_emails(
            domain=domain,
            first_name=first or None,
            last_name=last or None,
            limit=3,
        )
        for c in candidates:
            verdict = await verifier.verify(c.email)
            if verdict.status == "valid":
                lead.contact_email = c.email
                lead.email_found = True
                lead.email_verified = True
                lead.contact_first_name = c.first_name or lead.contact_first_name
                lead.contact_last_name = c.last_name or lead.contact_last_name
                lead.contact_title = c.position or lead.contact_title
                await session.commit()
                return
        if candidates:
            lead.contact_email = candidates[0].email
            lead.email_found = True
            lead.email_verified = False
            await session.commit()
        else:
            await session.commit()


@router.post("/enrich-lead/{lead_id}")
async def enrich_lead_emails(
    lead_id: UUID,
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger email finding and verification for a lead."""
    background_tasks.add_task(_enrich_lead_emails, lead_id)
    return {"status": "accepted", "lead_id": str(lead_id), "message": "Enrichment started"}


@router.post("/enrich-lead/{lead_id}/sync")
async def enrich_lead_emails_sync(lead_id: UUID) -> dict:
    """Synchronously enrich a lead (find email, verify, company data)."""
    await _enrich_lead_emails(lead_id)
    async with AsyncSessionFactory() as session:
        lead = await session.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {
            "lead_id": str(lead_id),
            "email_found": lead.email_found,
            "email_verified": lead.email_verified,
            "contact_email": lead.contact_email,
        }
