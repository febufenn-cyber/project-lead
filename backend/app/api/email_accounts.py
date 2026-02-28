"""Email accounts for campaign sending."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EmailAccount

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])


class EmailAccountCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    display_name: str | None = None
    smtp_host: str = Field(min_length=2, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None
    use_tls: bool = True
    daily_limit: int = Field(default=100, ge=1, le=1000)


@router.post("")
async def create_email_account(
    payload: EmailAccountCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    acct = EmailAccount(
        email=payload.email,
        display_name=payload.display_name,
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_user=payload.smtp_user,
        smtp_password_encrypted=payload.smtp_password,
        use_tls=payload.use_tls,
        daily_limit=payload.daily_limit,
    )
    session.add(acct)
    await session.commit()
    await session.refresh(acct)
    return {"id": str(acct.id), "email": acct.email}


@router.get("")
async def list_email_accounts(session: AsyncSession = Depends(get_db)) -> list:
    result = await session.execute(select(EmailAccount).order_by(EmailAccount.created_at.desc()))
    accounts = result.scalars().all()
    return [
        {"id": str(a.id), "email": a.email, "display_name": a.display_name, "is_active": a.is_active}
        for a in accounts
    ]
