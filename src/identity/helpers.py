from fastapi import Header

from src.constants import AssertionErrorMessage
from src.identity.schemas import SigninWithAppleHeader


def parse_apple_id_token(id_token: str = Header(...)) -> SigninWithAppleHeader:
    assert id_token is not None, AssertionErrorMessage.INVALID_TOKEN

    return SigninWithAppleHeader(id_token=id_token)
