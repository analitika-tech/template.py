import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.response import bad_request, ok, unauthorized
from src.config import Settings
from src.constants import AssertionErrorMessage
from src.dependencies import get_db, get_settings
from src.identity.dependencies import (
    get_apple_identity_provider_service,
    get_google_identity_provider_service,
    get_identity_service,
    is_authenticated,
    oauth2_scheme,
)
from src.identity.helpers import parse_apple_id_token
from src.identity.schemas import (
    ConfirmUserEmailRequest,
    CreateUserRequest,
    DeleteProfile,
    QueryIdentityByEmail,
    SigninCallbackRequest,
    SigninRedirectRequest,
    SigninWithAppleHeader,
    SigninWithAppleRequest,
    SigninWithAppleRequestWeb,
    TokenResponse,
    UserInfo,
)
from src.identity.services import (
    IdentityProvider,
    IdentityService,
    confirm_email,
    create_user,
    delete_user,
    get_or_create_user,
    get_user,
)
from src.models import Result

api = APIRouter(prefix="/identity", tags=["identity"])
web = APIRouter(prefix="/identity", tags=["web-identity"])

logger = logging.getLogger(__name__)


def get_refresh_token(request: Request) -> Result[str, None]:
    cookies = request.cookies
    assert cookies is not None, AssertionErrorMessage.INVALID_TOKEN

    assert cookies.get("refresh_token") is not None, AssertionErrorMessage.INVALID_TOKEN

    return cookies.get("refresh_token")


@api.post(
    "/signin/redirect",
    response_model=Result[str, None],
)
async def signin_redirect(
    request: SigninRedirectRequest,
    identity_provider: IdentityProvider = Depends(get_google_identity_provider_service),
):
    assert (
        request.id is not None and len(request.id.strip()) > 1
    ), AssertionErrorMessage.invalid_property("request.id")

    return ok(Result[str, None].success(identity_provider.signin_redirect(request.id)))


@api.get("/signin/redirect/callback/deeplink")
async def google_signin_callback_deeplink(code: str):
    assert code is not None, AssertionErrorMessage.invalid_property("code")
    logger.info(f"Authorization Code: {code}")

    return RedirectResponse(f"billastiq://callback?code={code}")


@api.get("/signin/redirect/callback")
async def signin_redirect_callback_route(
    request: SigninCallbackRequest = Depends(),
    identity_provider: IdentityProvider = Depends(get_google_identity_provider_service),
    session: AsyncSession = Depends(get_db),
    identity_service: IdentityService = Depends(get_identity_service),
    settings: Settings = Depends(get_settings),
):
    client = settings.google_mobile.id

    callback = await identity_provider.signin_callback(request.code, client)
    if not callback.succeeded:
        return bad_request(
            Result[TokenResponse, None].failed_list(callback.errors),
        )

    user_info = await identity_provider.get_user_info(callback.data)
    if not user_info.succeeded:
        return bad_request(
            Result[TokenResponse, None].failed_list(user_info.errors),
        )

    user_info.data.idp = "google"

    result = await get_or_create_user(session, user_info.data)
    if not result.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(result.errors))

    token_result = identity_service.authenticate(result.data)

    if not token_result.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(token_result.errors))

    return ok(token_result)


@api.post("/signin/redirect/callback/apple")
async def signin_redirect_callback_apple(
    request: SigninWithAppleRequest,
    header: SigninWithAppleHeader = Depends(parse_apple_id_token),
    identity_provider: IdentityProvider = Depends(get_apple_identity_provider_service),
    session: AsyncSession = Depends(get_db),
    identity_service: IdentityService = Depends(get_identity_service),
):
    validation = await identity_provider.validate_id_token(header.id_token)
    if not validation.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(validation.errors))

    user_info = await identity_provider.get_user_info(
        TokenResponse(id_token=header.id_token)
    )

    if not user_info.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(user_info.errors))

    user_info.data.given_name = request.given_name
    user_info.data.family_name = request.family_name
    user_info.data.email = request.email
    user_info.data.email_verified = True
    user_info.data.idp = "apple"

    result = await get_or_create_user(session, user_info.data)
    if not result.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(result.errors))

    token_result = identity_service.authenticate(result.data)

    if not token_result.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(token_result.errors))

    return ok(token_result)


@api.post(
    "/token/refresh",
    response_model=Result[TokenResponse, None],
    description="In the Authorization header provide us with your access_token recieved from our server [**Authorization Bearer <access_token>]** and in the cookie header provide us the refresh token **[Cookie: refresh_token=<refresh_token>]**",
)
async def refresh_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    refresh_token: str = Depends(get_refresh_token),
    session: AsyncSession = Depends(get_db),
    identity_service: IdentityService = Depends(get_identity_service),
    settings: Settings = Depends(get_settings),
):
    is_authenticated_result = identity_service.is_access_token_valid(token)
    if is_authenticated_result:
        return ok(
            Result[TokenResponse, None].success(
                TokenResponse(
                    access_token=token,
                    refresh_token=refresh_token,
                    expires_in=settings.access_token_lifetime,
                    token_type="Bearer",
                )
            )
        )

    validation_result = identity_service.validate_refresh_token(refresh_token)

    user_result = await get_user(session, validation_result.data)
    if not user_result.succeeded:
        return unauthorized(Result[TokenResponse, None].failed_list(user_result.errors))

    result = identity_service.authenticate(user_result.data)
    if not result.succeeded:
        return bad_request(Result[TokenResponse, None].failed_list(result.errors))

    return ok(result)


@api.get("/userinfo")
async def get_user_info(
    info: Annotated[Result[UserInfo, None], Depends(is_authenticated)],
    session: AsyncSession = Depends(get_db),
):
    user = await get_user(session, info.data)
    if not user.succeeded:
        return bad_request(Result[UserInfo, None].failed_list(user.errors))

    return ok(Result[UserInfo, None].success(UserInfo.from_entity(user.data)))


@api.delete("/apple/delete")
async def delete_user_apple(
    request: DeleteProfile,
    info: Annotated[Result[UserInfo, None], Depends(is_authenticated)],
    identity_provider: IdentityProvider = Depends(get_apple_identity_provider_service),
    session: AsyncSession = Depends(get_db),
):
    await identity_provider.revoke(request.code, "")

    await delete_user(session, info.data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api.delete("/google/delete")
async def delete_user_google(
    request: DeleteProfile,
    info: Annotated[Result[UserInfo, None], Depends(is_authenticated)],
    identity_provider: IdentityProvider = Depends(get_google_identity_provider_service),
    session: AsyncSession = Depends(get_db),
):
    await identity_provider.revoke(request.code, request.id)

    await delete_user(session, info.data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api.post("/register", response_model=Result[None, None])
async def create_user_route(
    request: CreateUserRequest,
    base_request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    request._host_url = base_request.base_url

    result = await create_user(session, settings, request)

    if not result.succeeded:
        return bad_request(result)

    return ok(result)


@api.get("/confirm", response_model=Result[None, None])
async def create_user_route(
    request: ConfirmUserEmailRequest = Depends(),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):

    result = await confirm_email(session, settings, request)

    if not result.succeeded:
        return bad_request(result)

    return ok(result)
