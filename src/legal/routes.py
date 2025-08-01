from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse

from src.common.response import ok
from src.legal.constants import PRIVACY_POLICY
from src.models import Result

legal_router = APIRouter(prefix="/legal")


@legal_router.get(
    "/api/privacy-policy",
    status_code=status.HTTP_200_OK,
    response_model=Result[str, None],
)
async def get_privacy_policy():
    return ok(
        Result[str, None].success(PRIVACY_POLICY),
    )
