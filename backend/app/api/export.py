from fastapi import APIRouter

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/status")
async def export_status() -> dict[str, str]:
    return {"status": "ready"}
