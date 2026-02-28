"""Organizations, API keys, and webhooks API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey, Organization, OrgMember, Webhook
from app.models.api_key import generate_api_key_secret

router = APIRouter(prefix="/orgs", tags=["organizations"])


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = None


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    created_at: str
    is_active: bool


class WebhookCreate(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    events: list[str] = Field(default_factory=lambda: ["lead.created"])
    description: str | None = None


@router.post("", response_model=dict)
async def create_org(
    payload: OrgCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    slug = payload.slug or payload.name.lower().replace(" ", "-")[:50]
    org = Organization(name=payload.name, slug=slug)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return {"id": str(org.id), "name": org.name, "slug": org.slug}


@router.get("", response_model=list)
async def list_orgs(session: AsyncSession = Depends(get_db)) -> list:
    result = await session.execute(select(Organization).order_by(Organization.name))
    orgs = result.scalars().all()
    return [{"id": str(o.id), "name": o.name, "slug": o.slug} for o in orgs]


@router.post("/{org_id}/api-keys", response_model=dict)
async def create_api_key(
    org_id: UUID,
    payload: ApiKeyCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    secret = generate_api_key_secret()
    prefix = secret[:12]
    import hashlib
    key_hash = hashlib.sha256(secret.encode()).hexdigest()
    api_key = ApiKey(
        org_id=org_id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
    )
    session.add(api_key)
    await session.commit()
    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": secret,
        "key_prefix": prefix,
        "warning": "Store the key securely. It will not be shown again.",
    }


@router.get("/{org_id}/api-keys", response_model=list)
async def list_api_keys(
    org_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list:
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    result = await session.execute(
        select(ApiKey).where(ApiKey.org_id == org_id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {"id": str(k.id), "name": k.name, "key_prefix": k.key_prefix, "is_active": k.is_active}
        for k in keys
    ]


@router.delete("/{org_id}/api-keys/{key_id}")
async def revoke_api_key(
    org_id: UUID,
    key_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    api_key = await session.get(ApiKey, key_id)
    if not api_key or api_key.org_id != org_id:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    await session.commit()
    return {"status": "revoked"}


@router.post("/{org_id}/webhooks", response_model=dict)
async def create_webhook(
    org_id: UUID,
    payload: WebhookCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    webhook = Webhook(
        org_id=org_id,
        url=payload.url,
        events=payload.events,
        description=payload.description,
    )
    session.add(webhook)
    await session.commit()
    await session.refresh(webhook)
    return {"id": str(webhook.id), "url": webhook.url, "events": webhook.events}


@router.get("/{org_id}/webhooks", response_model=list)
async def list_webhooks(
    org_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> list:
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    result = await session.execute(
        select(Webhook).where(Webhook.org_id == org_id).order_by(Webhook.created_at.desc())
    )
    webhooks = result.scalars().all()
    return [
        {"id": str(w.id), "url": w.url, "events": w.events, "is_active": w.is_active}
        for w in webhooks
    ]
