from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

TData = TypeVar("TData")
TInfo = TypeVar("TInfo")


@dataclass
class Error:
    code: str
    description: str


@dataclass
class Result(Generic[TData, TInfo]):
    succeeded: bool
    data: TData
    errors: List[Error]
    info: Optional[TInfo] = None

    @staticmethod
    def success(result: Optional[TData] = None, info: Optional[TInfo] = None):
        return Result[TData, TInfo](succeeded=True, data=result, errors=[], info=info)

    @staticmethod
    def failed(code: str, description: str):
        error = Error(code, description)

        return Result[TData, TInfo](succeeded=False, data=None, errors=[error])

    @staticmethod
    def failed_list(errors: list[Error]):
        return Result[TData, TInfo](succeeded=False, data=None, errors=errors)
