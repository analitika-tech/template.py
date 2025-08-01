from typing import Any

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.models import Result


def ok(result: Result[Any, Any]):
    return to_response(status.HTTP_200_OK, result)


def no_content(result: Result[Any, Any]):
    return to_response(status.HTTP_204_NO_CONTENT, result)


def multi_status(result: Result[Any, Any]):
    return to_response(status.HTTP_207_MULTI_STATUS, result)


def bad_request(result: Result[Any, Any]):
    return to_response(status.HTTP_400_BAD_REQUEST, result)


def unauthorized(result: Result[Any, Any]):
    return to_response(status.HTTP_401_UNAUTHORIZED, result)


def to_response(status_code: int, result: Result[Any, Any]):
    """
    Returns a envoded json response from the result object
    """
    return JSONResponse(status_code=status_code, content=jsonable_encoder(result))
