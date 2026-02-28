import csv
import io
from typing import Iterable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Lead
from app.schemas import LeadListResponse, LeadResponse

router = APIRouter(prefix="/leads", tags=["leads"])


def _serialize_csv(leads: Iterable[Lead]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "job_id",
            "company_name",
            "company_website",
            "company_phone",
            "company_email",
            "street",
            "city",
            "state",
            "country",
            "rating",
            "review_count",
            "lead_score",
            "source",
        ]
    )

    for lead in leads:
        writer.writerow(
            [
                str(lead.id),
                str(lead.job_id),
                lead.company_name,
                lead.company_website or "",
                lead.company_phone or "",
                (lead.contact_email or lead.company_email) or "",
                lead.street or "",
                lead.city or "",
                lead.state or "",
                lead.country or "",
                lead.rating if lead.rating is not None else "",
                lead.review_count if lead.review_count is not None else "",
                lead.lead_score,
                lead.source,
            ]
        )

    return buffer.getvalue()


@router.get("", response_model=LeadListResponse)
async def list_leads(
    q: str | None = Query(default=None),
    city: str | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=0, le=100),
    job_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> LeadListResponse:
    filters = []

    if q:
        like = f"%{q}%"
        filters.append(
            or_(
                Lead.company_name.ilike(like),
                Lead.company_website.ilike(like),
                Lead.street.ilike(like),
            )
        )

    if city:
        filters.append(Lead.city.ilike(city))

    if min_score is not None:
        filters.append(Lead.lead_score >= min_score)

    if job_id:
        filters.append(Lead.job_id == job_id)

    where_clause = and_(*filters) if filters else None

    count_query = select(func.count()).select_from(Lead)
    data_query = select(Lead).order_by(Lead.lead_score.desc(), Lead.created_at.desc()).offset(offset).limit(limit)

    if where_clause is not None:
        count_query = count_query.where(where_clause)
        data_query = data_query.where(where_clause)

    total = await session.scalar(count_query)
    result = await session.execute(data_query)

    items = [LeadResponse.model_validate(lead) for lead in result.scalars().all()]
    return LeadListResponse(total=total or 0, items=items)


@router.get("/export/csv")
async def export_leads_csv(
    job_id: UUID | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=0, le=100),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    filters = []
    if job_id:
        filters.append(Lead.job_id == job_id)
    if min_score is not None:
        filters.append(Lead.lead_score >= min_score)

    query = select(Lead).order_by(Lead.lead_score.desc())
    if filters:
        query = query.where(and_(*filters))

    result = await session.execute(query)
    csv_string = _serialize_csv(result.scalars().all())

    return StreamingResponse(
        iter([csv_string]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, session: AsyncSession = Depends(get_db)) -> LeadResponse:
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)
