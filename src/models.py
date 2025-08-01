import datetime
import uuid
from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

from sqlalchemy import UUID, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now()
    )


@dataclass
class Error:
    code: str
    description: str


TData = TypeVar("TData")
TInfo = TypeVar("TInfo")


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
