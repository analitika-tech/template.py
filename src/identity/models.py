from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models import Base


class User(Base):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(
        String, index=True, unique=True, nullable=False
    )
    password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_email_confirmed: Mapped[bool] = mapped_column(
        Boolean(create_constraint=False)
    )
    picture: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    birthday: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    idp: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    def __full_name__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @staticmethod
    def to_dict(user: "User") -> dict:
        assert user is not None
        return dict(
            given_name=user.first_name,
            family_name=user.last_name,
            email=user.email,
            sub=str(user.id),
            idp=user.idp,
        )
