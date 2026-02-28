"""Billing and credits API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CreditUsage, Organization, Plan, Subscription

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
async def list_plans(session: AsyncSession = Depends(get_db)) -> list:
    result = await session.execute(select(Plan).order_by(Plan.price_cents))
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "credits_per_month": p.credits_per_month,
            "price_cents": p.price_cents,
        }
        for p in plans
    ]


@router.get("/org/{org_id}/usage")
async def get_org_usage(
    org_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    sub_result = await session.execute(
        select(Subscription).where(
            Subscription.org_id == org_id,
            Subscription.status == "active",
        ).limit(1)
    )
    sub = sub_result.scalar_one_or_none()
    plan = await session.get(Plan, sub.plan_id) if sub and sub.plan_id else None
    credits_limit = plan.credits_per_month if plan else 0

    usage_result = await session.execute(
        select(func.sum(CreditUsage.amount)).where(CreditUsage.org_id == org_id)
    )
    used = usage_result.scalar() or 0

    return {
        "org_id": str(org_id),
        "credits_used": used,
        "credits_limit": credits_limit,
        "plan": plan.name if plan else None,
    }


class RecordUsageRequest(BaseModel):
    org_id: UUID
    action_type: str = Field(min_length=1, max_length=64)
    amount: int = Field(default=1, ge=1)


@router.post("/usage")
async def record_usage(
    payload: RecordUsageRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    org = await session.get(Organization, payload.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    usage = CreditUsage(
        org_id=payload.org_id,
        action_type=payload.action_type,
        amount=payload.amount,
    )
    session.add(usage)
    await session.commit()
    return {"status": "recorded", "action_type": payload.action_type, "amount": payload.amount}
