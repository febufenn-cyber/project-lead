from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register() -> dict[str, str]:
    return {"message": "Registration endpoint scaffolded"}


@router.post("/login")
async def login() -> dict[str, str]:
    return {"message": "Login endpoint scaffolded"}
