import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.common.models import Error, Result
from src.constants import ErrorCode, ErrorMessage

logger = logging.getLogger(__name__)


class UnauthorizedException(Exception):
    """
    result: regular result obj
    is_web: checks if the authoirzation happened on web or api, if web it will redirect user to login on web, else it will return result obj with 401 unauthorized to api
    """

    def __init__(self, result: Result):
        self.result = result


async def unauthorized_exception_handler(_: Request, ex: UnauthorizedException):
    """Throwing HTTP Unauthorized exceptions where the token validation fails"""
    logger.error("User not authorized to get access to the resource")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=jsonable_encoder(ex.result),
    )


async def global_exception_handler(_: Request, ex: Exception):
    logger.error(f"Internal server error with exception: {ex}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            Result[str, None].failed(
                ErrorCode.INTERNAL_SERVER_ERROR,
                ErrorMessage.INTERNAL_SERVER_ERROR,
            )
        ),
    )


async def assertion_exception_handler(_: Request, ex: AssertionError):
    logger.error(ex)

    errors: list[Error] = [Error("AssertionError", error) for error in ex.args]

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            Result[str, None].failed_list(errors),
        ),
    )


def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AssertionError, assertion_exception_handler)
    app.add_exception_handler(UnauthorizedException, unauthorized_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
