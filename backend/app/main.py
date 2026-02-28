from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.campaigns import router as campaigns_router
from app.api.billing import router as billing_router
from app.api.email_accounts import router as email_accounts_router
from app.api.orgs import router as orgs_router
from app.api.pipelines import router as pipelines_router
from app.api.email import router as email_router
from app.api.score import router as score_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.leads import router as leads_router
from app.config import get_settings
from app.database import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)
app.include_router(leads_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(billing_router, prefix=settings.api_prefix)
app.include_router(orgs_router, prefix=settings.api_prefix)
app.include_router(email_accounts_router, prefix=settings.api_prefix)
app.include_router(campaigns_router, prefix=settings.api_prefix)
app.include_router(pipelines_router, prefix=settings.api_prefix)
app.include_router(score_router, prefix=settings.api_prefix)
app.include_router(email_router, prefix=settings.api_prefix)
app.include_router(export_router, prefix=settings.api_prefix)
