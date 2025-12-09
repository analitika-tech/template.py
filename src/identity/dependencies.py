from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.common.models import Result
from src.identity.schemas import UserInfo
from src.identity.services import (
    AppleIdentityProviderService,
    GoogleIdentityProviderService,
    IdentityProvider,
    IdentityService,
)
from src.settings.dependencies import get_settings
from src.settings.models import Settings

auth_scheme = HTTPBearer()


async def get_google_identity_provider_service(
    settings: Settings = Depends(get_settings),
) -> IdentityProvider:
    from src.identity.services import IdentityModel

    document = await IdentityModel.get_discovery_document(settings.google_mobile.idp)
    return GoogleIdentityProviderService(settings, document.data)


def get_apple_identity_provider_service(
    settings: Settings = Depends(get_settings),
) -> IdentityProvider:
    from src.identity.services import DiscoveryDocument

    document = DiscoveryDocument(
        authorization_endpoint="",
        token_endpoint=settings.apple_token_uri,
        userinfo_endpoint="",
        jwks_uri=settings.apple_jwks_uri,
        revocation_endpoint=settings.apple_revoke_uri,
    )

    return AppleIdentityProviderService(settings, document)


def get_identity_service(
    settings: Settings = Depends(get_settings),
) -> IdentityService:
    return IdentityService(settings)


def is_authenticated(
    bearer: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)],
    identity_service: IdentityService = Depends(get_identity_service),
) -> Result[UserInfo, None]:
    """DI for checking if the token issued is valid, the token has to be issued by our backend server"""
    return identity_service.is_authenticated(bearer.credentials)
