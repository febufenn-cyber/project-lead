from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def api_health() -> dict[str, str]:
    """Health check for API consumers and infrastructure probes."""
    return {"status": "ok"}
