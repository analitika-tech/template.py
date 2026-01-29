import asyncio
import base64
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
import requests
from passlib.context import CryptContext
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common import email
from src.common.exceptions import UnauthorizedException
from src.common.models import Result
from src.constants import AssertionErrorMessage, ErrorCode, ErrorMessage
from src.identity.models import User
from src.identity.schemas import (
    AuthorizationCodeRequest,
    ConfirmUserEmailRequest,
    CreateUserRequest,
    DiscoveryDocument,
    PeopleBirthdayData,
    PeopleGenderInfo,
    PeopleInfoResponse,
    TokenResponse,
    UserInfo,
)
from src.settings.models import GoogleSigninSettings, Settings

logger = logging.getLogger(__name__)


class IdentityProvider(ABC):

    @abstractmethod
    def signin_redirect(self, id: str) -> str:
        pass

    @abstractmethod
    async def signin_callback(
        self, code: str, id: str
    ) -> Result[TokenResponse, None]:
        pass

    @abstractmethod
    async def get_user_info(
        self, token: TokenResponse
    ) -> Result[UserInfo, None]:
        pass

    @abstractmethod
    async def validate_id_token(self, token: str) -> Result[bool, None]:
        pass

    @abstractmethod
    async def revoke(self, code: str) -> Result[bool, None]:
        pass

    @abstractmethod
    async def revoke(self, code: str, id: str) -> Result[bool, None]:
        pass


class IdentityModel:
    @staticmethod
    async def get_discovery_document(
        issuer_uri: str,
    ) -> Result[DiscoveryDocument, None]:
        url = f"{issuer_uri}/.well-known/openid-configuration"

        result = await asyncio.to_thread(requests.get, url)

        if result.status_code != 200:
            return Result[DiscoveryDocument, None].failed(
                ErrorCode.INVALID_DISCOVERY_DOCUMENT_ENDPOINT,
                ErrorMessage.INVALID_DISCOVERY_DOCUMENT_ENDPOINT,
            )

        return Result[DiscoveryDocument, None].success(
            DiscoveryDocument(**result.json())
        )

    @staticmethod
    async def get_user_info(
        token: str, document: DiscoveryDocument
    ) -> Result[UserInfo, None]:
        assert (
            document is not None
        ), AssertionErrorMessage.INVALID_DISCOVERY_DOCUMENT

        result = await asyncio.to_thread(
            requests.get,
            document.userinfo_endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )

        if result.status_code != 200:
            return Result[UserInfo, None].failed(
                ErrorCode.INVALID_TOKEN,
                ErrorMessage.INVALID_TOKEN,
            )

        return Result[UserInfo, None].success(UserInfo(**result.json()))

    @staticmethod
    async def request_authorization_code_token(
        request: AuthorizationCodeRequest, document: DiscoveryDocument
    ) -> Result[TokenResponse, None]:
        assert request is not None
        assert request.code is not None
        assert request.client_id is not None
        assert request.client_secret is not None
        assert request.redirect_uri is not None
        assert request.grant_type is not None
        assert request.grant_type == "authorization_code"
        assert document is not None

        result = await asyncio.to_thread(
            requests.post, document.token_endpoint, request.model_dump()
        )

        if result.status_code != 200:
            logger.error(
                f"Token couldn't be acquired and with response: {result.text}"
            )
            return Result[TokenResponse, None].failed(
                ErrorCode.INVALID_TOKEN,
                ErrorMessage.INVALID_TOKEN,
            )

        return Result[TokenResponse, None].success(
            TokenResponse(**result.json())
        )


class AppleIdentityProviderService(IdentityProvider):
    def __init__(
        self, settings: Settings, document: DiscoveryDocument
    ) -> None:
        """
        For apple login verification will be using only validate_id_token\n
        discovery document will only have the jwks uri because apple has specific way of OAuth2
        """
        self._settings = settings
        self._document = document

    def _try_get_property(self, decoded: Any, key: str) -> Optional[str]:
        try:
            return decoded[key]
        except:
            return None

    def signin_redirect(self, id: str) -> str:
        raise NotImplementedError()

    async def signin_callback(
        self, code: str, id: str
    ) -> Result[TokenResponse, None]:
        raise NotImplementedError()

    async def get_user_info(
        self, token: TokenResponse
    ) -> Result[UserInfo, None]:
        assert (
            token.id_token is not None
        ), AssertionErrorMessage.INVALID_EXTERNAL_ACCESS_TOKEN
        assert (
            len(token.id_token) > 100
        ), AssertionErrorMessage.INVALID_EXTERNAL_ACCESS_TOKEN

        jwks_client = jwt.PyJWKClient(self._document.jwks_uri)
        header = jwt.get_unverified_header(token.id_token)

        assert header is not None, AssertionErrorMessage.INVALID_TOKEN_HADER
        assert (
            header["kid"] is not None
        ), AssertionErrorMessage.INVALID_TOKEN_HADER

        key_result = await asyncio.to_thread(
            jwks_client.get_signing_key, header["kid"]
        )

        decoded = jwt.decode(
            token.id_token,
            key_result.key,
            algorithms=[header["alg"]],
            options={"verify_aud": False, "verify_signature": False},
        )

        info = UserInfo(subject=decoded.get("sub"))

        return Result[UserInfo, None].success(info)

    async def validate_id_token(self, token: str) -> Result[bool, None]:
        try:
            assert (
                token is not None or len(token) < 100
            ), AssertionErrorMessage.INVALID_EXTERNAL_ACCESS_TOKEN

            jwks_client = jwt.PyJWKClient(self._document.jwks_uri)
            header = jwt.get_unverified_header(token)

            assert (
                header is not None
            ), AssertionErrorMessage.INVALID_TOKEN_HADER
            assert (
                header["kid"] is not None
            ), AssertionErrorMessage.INVALID_TOKEN_HADER

            key_result = await asyncio.to_thread(
                jwks_client.get_signing_key, header["kid"]
            )

            jwt.decode(
                token,
                key_result.key,
                algorithms=[header["alg"]],
                options={"verify_aud": False, "verify_signature": False},
            )

            return Result[bool, None].success(True)
        except Exception as ex:
            logger.error(ex)
            return Result[bool, None].failed(
                ErrorCode.INVALID_TOKEN, ErrorMessage.INVALID_TOKEN
            )

    async def revoke(self, code: str, id: str) -> Result[bool, None]:
        iat = datetime.now(timezone.utc)
        exp = iat + timedelta(seconds=5 * 60)

        payload = {
            "iss": self._settings.apple_team_id,
            "aud": "https://appleid.apple.com",
            "sub": self._settings.apple_client_id,
            "iat": iat,
            "exp": exp,
        }

        headers = {"algorithm": "ES256", "kid": self._settings.apple_key_id}

        token = jwt.encode(
            payload,
            base64.b64decode(self._settings.apple_login_cert_base64).decode(
                "utf-8"
            ),
            algorithm="ES256",
            headers=headers,
        )

        code_validation_request = await asyncio.to_thread(
            requests.post,
            self._document.token_endpoint,
            data={
                "client_id": self._settings.apple_client_id,
                "client_secret": token,
                "code": code,
                "grant_type": "authorization_code",
            },
        )

        if code_validation_request.status_code != 200:
            return Result[bool, None].failed(
                "InvalidCredentials",
                "Token revocation failed due to invalid credentials",
            )

        token_response = TokenResponse(**code_validation_request.json())

        revoke = await asyncio.to_thread(
            requests.post,
            self._settings.apple_revoke_uri,
            data={
                "client_id": self._settings.apple_client_id,
                "client_secret": token,
                "token": token_response.access_token,
            },
            headers={"Content-type": "application/x-www-form-urlencoded"},
        )

        if revoke.status_code != 200:
            return Result[bool, None].failed(
                "InvalidCredentials",
                "Token revocation failed due to invalid credentials",
            )

        return Result[bool, None].success()


class GoogleIdentityProviderService(IdentityProvider):
    def __init__(
        self, settings: Settings, document: DiscoveryDocument
    ) -> None:
        self._settings = settings
        self._document = document

        assert settings is not None
        assert document is not None

    def _filter_clients(self, id: str) -> Optional[GoogleSigninSettings]:
        assert id is not None, AssertionErrorMessage.invalid_property("id")
        return next(
            client
            for client in [
                self._settings.google_mobile,
            ]
            if client.id == id
        )

    def signin_redirect(self, id: str) -> str:
        """Returns a signin redirect uri to Google Authentication with following scopes:
        - openid
        - profile
        - email
        - https://www.googleapis.com/auth/user.birthday.read - apple denies use if no user benefit
        - https://www.googleapis.com/auth/user.gender.read - apple denies use if no user benefit
        """

        assert (
            id is not None and len(id) > 0
        ), AssertionErrorMessage.invalid_property("request.id")

        client = self._filter_clients(id)

        assert client is not None, AssertionErrorMessage.entity_not_found(
            "Client"
        )

        return f"{self._document.authorization_endpoint}?response_type=code&client_id={client.client_id}&redirect_uri={client.redirect_uri}&scope=openid%20profile%20email&aacess_type=offline"

    async def signin_callback(
        self, code: str, id: str
    ) -> Result[TokenResponse, None]:
        assert code is not None

        client = self._filter_clients(id)

        assert client is not None

        request = AuthorizationCodeRequest(
            code=code,
            client_id=client.client_id,
            client_secret=client.client_secret,
            redirect_uri=client.redirect_uri,
        )

        result = await IdentityModel.request_authorization_code_token(
            request, self._document
        )

        if not result.succeeded:
            return Result[TokenResponse, None].failed_list(result.errors)

        assert (
            result.data.access_token is not None
        ), AssertionErrorMessage.invalid_property("access_token")

        return result

    async def get_user_info(
        self, token: TokenResponse
    ) -> Result[UserInfo, None]:
        assert (
            token.access_token is not None
        ), AssertionErrorMessage.INVALID_EXTERNAL_ACCESS_TOKEN

        info_result = await IdentityModel.get_user_info(
            token.access_token, self._document
        )

        if not info_result.succeeded:
            return Result[UserInfo, None].failed_list(info_result.errors)

        assert (
            info_result.data.given_name is not None
        ), AssertionErrorMessage.invalid_property("given_name")
        assert (
            info_result.data.family_name is not None
        ), AssertionErrorMessage.invalid_property("family_name")
        assert (
            info_result.data.email is not None
        ), AssertionErrorMessage.invalid_property("email")
        assert (
            info_result.data.email_verified is not None
        ), AssertionErrorMessage.invalid_property("email_verified")

        # Refactor this part with the apple login part
        if token.id_token is not None:
            jwks_client = jwt.PyJWKClient(self._document.jwks_uri)
            header = jwt.get_unverified_header(token.id_token)

            assert (
                header is not None
            ), AssertionErrorMessage.INVALID_TOKEN_HADER
            assert (
                header["kid"] is not None
            ), AssertionErrorMessage.INVALID_TOKEN_HADER

            key_result = await asyncio.to_thread(
                jwks_client.get_signing_key, header["kid"]
            )

            decoded = jwt.decode(
                token.id_token,
                key_result.key,
                algorithms=[header["alg"]],
                options={"verify_aud": False, "verify_signature": False},
            )

            info_result.data.subject = decoded.get("sub")

        # additional_info_result = await self._request_additional_user_info(access_token)
        # if not additional_info_result.succeeded:
        # return Result[UserInfo].failed_list(additional_info_result.errors)

        # info = self._update_user_info(additional_info_result.data, info_result.data)

        # assert info.birthday is not None, AssertionErrorMessage.invalid_property(
        #    "birthday"
        # )
        # assert info.gender is not None, AssertionErrorMessage.invalid_property("gender")

        return Result[UserInfo, None].success(info_result.data)

    async def validate_id_token(self, token: str) -> Result[bool, None]:
        try:
            assert (
                token is not None or len(token) < 100
            ), AssertionErrorMessage.INVALID_EXTERNAL_ACCESS_TOKEN

            jwks_client = jwt.PyJWKClient(self._document.jwks_uri)
            header = jwt.get_unverified_header(token)

            assert (
                header is not None
            ), AssertionErrorMessage.INVALID_TOKEN_HADER
            assert (
                header["kid"] is not None
            ), AssertionErrorMessage.INVALID_TOKEN_HADER

            key_result = await asyncio.to_thread(
                jwks_client.get_signing_key, header["kid"]
            )

            jwt.decode(
                token,
                key_result.key,
                algorithms=[header["alg"]],
                options={"verify_aud": False, "verify_signature": False},
            )

            return Result[bool, None].success(True)
        except Exception as ex:
            logger.error(ex)
            return Result[bool, None].failed(
                ErrorCode.INVALID_TOKEN, ErrorMessage.INVALID_TOKEN
            )

    async def revoke(self, code: str, id: str) -> Result[bool, None]:
        assert code is not None, AssertionErrorMessage.INVALID_TOKEN

        token = await self.signin_callback(code, id)
        if not token.succeeded:
            return Result[bool, None].failed_list(token.errors)

        assert (
            token.data.access_token is not None
        ), AssertionErrorMessage.INVALID_TOKEN

        result = await asyncio.to_thread(
            requests.post,
            self._document.revocation_endpoint,
            {"token": token.data.access_token},
        )

        if result.status_code != 200:
            return Result[bool, None].failed(
                "RevocationError", "User data not valid"
            )

        return Result[bool, None].success()

    async def _request_additional_user_info(
        self, access_token: str
    ) -> Result[PeopleInfoResponse, None]:
        assert (
            access_token is not None or len(access_token) < 200
        ), AssertionErrorMessage.INVALID_EXTERNAL_ACCESS_TOKEN
        assert (
            self._settings.google_people_api_key is not None
        ), AssertionErrorMessage.invalid_property("google_people_api_key")

        result = await asyncio.to_thread(
            requests.get,
            f"https://people.googleapis.com/v1/people/me?key={self._settings.google_people_api_key}&personFields=genders,birthdays",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if result.status_code != 200:
            return Result[PeopleInfoResponse, None].failed(
                ErrorCode.INVALID_REQUEST,
                ErrorMessage.INVALID_REQUEST,
            )

        return Result[PeopleInfoResponse, None].success(
            PeopleInfoResponse(**result.json())
        )

    def _update_user_info(
        self, additional_info: PeopleInfoResponse, user_info: UserInfo
    ) -> UserInfo:
        user_info.birthday = self._get_birthday(additional_info.birthdays)
        user_info.gender = self._get_gender(additional_info.genders)

        return user_info

    def _get_gender(self, genders: list[PeopleGenderInfo]) -> str:
        assert genders is not None and len(genders) > 0

        return genders[0].formatted_value

    def _get_birthday(self, birthdays: list[PeopleBirthdayData]) -> datetime:
        assert birthdays is not None and len(birthdays) > 0

        birthday_object = [
            value.date
            for value in birthdays
            if value.date.day is not None
            and value.date.month is not None
            and value.date.year is not None
        ][0]

        return datetime.strptime(
            f"{birthday_object.year}-{birthday_object.month}-{birthday_object.day}",
            "%Y-%m-%d",
        )


class IdentityService:
    def __init__(self, settings: Settings):
        self._settings = settings

    def authenticate(self, user: User) -> Result[TokenResponse, None]:
        access_token = self.generate_access_token(user)
        assert access_token is not None, AssertionErrorMessage.INVALID_TOKEN

        refresh_token = self.generate_refresh_token(user)
        assert refresh_token is not None, AssertionErrorMessage.INVALID_TOKEN

        return Result[TokenResponse, None].success(
            TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self._settings.access_token_lifetime,
                token_type="Bearer",
            )
        )

    def generate_access_token(self, user: User) -> str:
        assert (
            self._settings.access_token_lifetime is not None
            and self._settings.access_token_lifetime > 0
            and isinstance(self._settings.access_token_lifetime, int)
        ), AssertionErrorMessage.INVALID_TOKEN_LIFETIME

        assert (
            self._settings.access_token_secret is not None
            and isinstance(self._settings.access_token_secret, str)
            and len(self._settings.access_token_secret) > 0
        ), AssertionErrorMessage.INVALID_TOKEN_SECRET

        assert (
            self._settings.access_token_algorithm is not None
            and isinstance(self._settings.access_token_algorithm, str)
        ), (AssertionErrorMessage.INVALID_ALGORITHM)

        to_encode = User.to_dict(user)

        iat = datetime.now(timezone.utc)
        exp = iat + timedelta(seconds=self._settings.access_token_lifetime)

        assert exp > iat, AssertionErrorMessage.INVALID_TOKEN_LIFESPAN

        to_encode.update({"exp": exp})
        to_encode.update({"iat": iat})

        return jwt.encode(
            to_encode,
            self._settings.access_token_secret,
            algorithm=self._settings.access_token_algorithm,
        )

    def generate_refresh_token(self, user: User) -> str:
        assert (
            self._settings.refresh_token_lifetime is not None
            and self._settings.refresh_token_lifetime > 0
            and isinstance(self._settings.refresh_token_lifetime, int)
        ), AssertionErrorMessage.INVALID_TOKEN_LIFETIME

        assert (
            self._settings.refresh_token_secret is not None
            and isinstance(self._settings.refresh_token_secret, str)
            and len(self._settings.refresh_token_secret) > 0
        ), AssertionErrorMessage.INVALID_TOKEN_SECRET

        assert (
            self._settings.refresh_token_algorithm is not None
            and isinstance(self._settings.refresh_token_algorithm, str)
        ), (AssertionErrorMessage.INVALID_ALGORITHM)

        to_encode = User.to_dict(user)

        iat = datetime.now(timezone.utc)
        exp = iat + timedelta(seconds=self._settings.refresh_token_lifetime)

        assert exp > iat, AssertionErrorMessage.INVALID_TOKEN_LIFESPAN

        del to_encode["family_name"]
        del to_encode["given_name"]

        to_encode.update({"exp": exp})
        to_encode.update({"iat": iat})
        to_encode.update({"token_type": "refresh"})

        return jwt.encode(
            to_encode,
            self._settings.refresh_token_secret,
            algorithm=self._settings.refresh_token_algorithm,
        )

    def is_authenticated(self, token: str) -> Result[UserInfo, None]:
        assert token is not None, AssertionErrorMessage.INVALID_TOKEN
        try:
            payload = jwt.decode(
                token,
                self._settings.access_token_secret,
                algorithms=[self._settings.access_token_algorithm],
            )

            info = UserInfo(
                given_name=payload.get("given_name"),
                family_name=payload.get("family_name"),
                id=payload.get("sub"),
                email=payload.get("email"),
            )

            return Result[UserInfo, None].success(info)
        except Exception as ex:
            raise UnauthorizedException(
                result=Result[UserInfo, None].failed(
                    ErrorCode.INVALID_TOKEN, str(ex)
                )
            )

    def is_access_token_valid(self, token: str) -> bool:
        try:
            self.is_authenticated(token)
            return True
        except:
            return False

    def validate_refresh_token(self, token: str) -> Result[UserInfo, None]:
        try:
            payload = jwt.decode(
                token,
                self._settings.refresh_token_secret,
                algorithms=[self._settings.refresh_token_algorithm],
            )

            assert (
                payload.get("email") is not None
            ), AssertionErrorMessage.INVALID_TOKEN

            return Result[UserInfo, None].success(
                UserInfo(email=payload.get("email"))
            )
        except Exception as ex:
            logger.error(ex)
            raise UnauthorizedException(
                result=Result[str, None].failed("InvalidToken", str(ex))
            )


async def get_user(
    session: AsyncSession, info: UserInfo
) -> Result[User, None]:

    query = select(User)
    if info.email is not None:
        query = query.where(User.email == info.email)

    if info.subject is not None:
        query = query.where(User.subject == info.subject)

    user = await session.scalar(query)
    if user is None:
        return Result[User, None].failed(
            ErrorCode.INVALID_USER, ErrorMessage.INVALID_USER
        )

    return Result[User, None].success(user)


async def get_or_create_user(
    session: AsyncSession, info: UserInfo
) -> Result[User, None]:
    try:
        assert (
            info.email is not None or info.subject is not None
        ), AssertionErrorMessage.INVALID_USER

        find_user = await get_user(session, info)
        if find_user.succeeded:
            return find_user

        assert info.email is not None, AssertionErrorMessage.invalid_property(
            "email"
        )
        assert (
            info.given_name is not None
        ), AssertionErrorMessage.invalid_property("given_name")
        assert (
            info.family_name is not None
        ), AssertionErrorMessage.invalid_property("family_name")
        assert (
            info.email_verified is not None
        ), AssertionErrorMessage.invalid_property("email_verified")
        user = UserInfo.to_entity(info)

        session.add(user)

        await session.commit()

        return Result[User, None].success(user)
    except Exception as ex:
        logger.error(ex)
        return Result[User, None].failed(
            ErrorCode.INVALID_USER, ErrorMessage.INVALID_USER
        )


async def delete_user(session: AsyncSession, info: UserInfo) -> None:
    await session.execute(delete(User).where(User.email == info.email))

    await session.commit()


async def send_confirmation_email(
    settings: Settings,
    request: CreateUserRequest,
    user_id: uuid.UUID,
) -> Result[None, None]:
    iat = datetime.now(timezone.utc)
    payload: dict = {
        "iat": iat,
        "exp": iat + timedelta(hours=settings.confirm_email_token_lifetime),
        "sub": str(user_id),
    }

    token = jwt.encode(
        payload,
        settings.confirm_email_token_secret,
        algorithm=settings.confirm_email_token_algorithm,
    )

    content = f"""
    <p style="font-family: Arial, sans-serif; font-size:14px; color:#333;">
      Hi {request.first_name} {request.last_name} ,<br>please confirm your email address to complete your registration.<br>
      Click the link below to verify your account:
      <br><br>
      <a href="{request._host_url}api/identity/confirm?token={token}" style="color:#1a73e8;">Confirm Email</a>
    </p>
    """

    await email.send(settings, content, request.email, "Confirm your email")

    return Result[None, None].success()


async def create_user(
    session: AsyncSession, settings: Settings, request: CreateUserRequest
) -> Result[None, None]:
    existing = await get_user(session, UserInfo(email=request.email))

    if existing.succeeded:
        return Result[None, None].failed(
            "ERR_USER_ALREADY_EXISTS", "User already exists!"
        )

    context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    password = context.hash(request.password)

    entity = request.to_entity(password)

    session.add(entity)

    await session.commit()

    await send_confirmation_email(settings, request, entity.id)

    return Result[None, None].success()


async def confirm_email(
    session: AsyncSession, settings: Settings, request: ConfirmUserEmailRequest
) -> Result[None, None]:
    try:
        payload: dict = jwt.decode(
            request.token,
            settings.confirm_email_token_secret,
            algorithms=[settings.confirm_email_token_algorithm],
        )

        sub = uuid.UUID(payload.get("sub"))

        if not sub:
            return Result[None, None].failed("ERR_EMAIL_CONFIRM_INVALID_SUB")

        user = await get_user(session, UserInfo(id=sub))
        if not user.succeeded:
            return Result[None, None].failed_list(user.errors)

        await session.execute(
            update(User).where(User.id == sub).values(is_email_confirmed=True)
        )

        await session.commit()

        return Result[None, None].success()
    except Exception as ex:
        logger.error(ex)
        return Result[None, None].failed(
            "ERR_EMAIL_CONFIRM_INVALID_TOKEN", "Provided token isn't valid!"
        )
