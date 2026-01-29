import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

from fastapi import Response
from pydantic import BaseModel

from src.common.schemas import BaseModelSchema
from src.identity.models import User


class DeleteProfile(BaseModel):
    code: str
    id: str


class SigninWithAppleHeader(BaseModel):
    id_token: str


class SigninWithAppleRequest(BaseModel):
    email: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class SigninRedirectRequest(BaseModel):
    id: str


class DiscoveryDocument(BaseModel):
    """
    Properties set to be optional due to Apple not providing discovery doc
    """

    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    revocation_endpoint: str


class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None
    id_token: Optional[str] = None


class UserInfo(BaseModel):
    id: Optional[Union[str, uuid.UUID]] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None
    gender: Optional[str] = None
    birthday: Optional[datetime] = None
    subject: Optional[str] = None
    idp: Optional[str] = None

    @staticmethod
    def to_entity(info: "UserInfo") -> User:
        return User(
            first_name=info.given_name,
            last_name=info.family_name,
            email=info.email,
            password=None,  # Update to hash password when the user is not issued by external provider
            is_email_confirmed=info.email_verified,
            picture=info.picture,
            gender=info.gender,
            birthday=info.birthday,
            subject=info.subject if info.subject is not None else "",
            idp=info.idp,
        )

    @staticmethod
    def from_entity(user: User) -> "UserInfo":
        return UserInfo(
            id=user.id,
            given_name=user.first_name,
            family_name=user.last_name,
            email=user.email,
            picture=user.picture,
            gender=user.gender,
            birthday=user.birthday,
            idp=user.idp,
        )

    @staticmethod
    def update_userinfo_model(
        info: "UserInfo", gender: str, birthday: datetime
    ) -> "UserInfo":
        assert info is not None
        assert gender is not None
        assert birthday is not None

        info.birthday = birthday
        info.gender = gender

        return info


class PeopleGenderInfo(BaseModelSchema):
    formatted_value: str


class PeopleBirthdayDateInfo(BaseModelSchema):
    year: Optional[int] = None
    month: int
    day: int


class PeopleBirthdayData(BaseModelSchema):
    date: PeopleBirthdayDateInfo


class PeopleInfoResponse(BaseModelSchema):
    genders: list[PeopleGenderInfo]
    birthdays: list[PeopleBirthdayData]


class ExternalSignInRequest(BaseModel):
    access_token: str
    id_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    access_token: str


class AuthorizationCodeRequest(BaseModel):
    code: str
    client_id: str
    client_secret: str
    redirect_uri: str
    grant_type: Optional[str] = "authorization_code"
    scope: Optional[str] = "openid profile email"


class SigninCallbackRequest(BaseModel):
    code: str


class SigninWithAppleUserName(BaseModelSchema):
    first_name: str
    last_name: str


class SigninWithAppleUser(BaseModelSchema):
    name: SigninWithAppleUserName
    email: str


class SigninWithAppleRequestWeb(BaseModel):
    code: str
    id_token: str
    user: Optional[SigninWithAppleUser] = None


class QueryIdentityByEmail(BaseModel):
    email: Optional[str] = None


@dataclass
class Auth:
    user: UserInfo
    response: Response


class ConfirmUserEmailRequest(BaseModelSchema):
    token: str


class CreateUserRequest(BaseModelSchema):
    first_name: str
    last_name: str
    email: str
    password: str

    _host_url: Optional[str] = None

    def to_entity(self, hashed_password: str) -> User:
        return User(
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
            subject=str(uuid.uuid4()),
            idp="local",
            password=hashed_password,
            is_email_confirmed=False,
        )
