from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.models import Error


base_model_config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
)

db_model_wrapper = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
)


class EntityToModelSchema(BaseModel):
    """
    Use this class when you want to convert entity to DTO/Model
    This will help you out and will convert from snake_case to pascalCase
    Alongside that you already have 2 predefined fields id, created_at which are contained in every model
    """

    id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    model_config = db_model_wrapper


class BaseModelSchema(BaseModel):
    model_config = base_model_config


class Pagination(BaseModelSchema):
    count: int
    page: int


class BaseFormSchema(BaseModel, ABC):
    model_config = base_model_config

    errors: List[Error] = []

    @abstractmethod
    def is_valid(self) -> bool:
        """
        Use the class properties to validate them, if something isn't valid create a Error(code, description) and append it to self.errors
        """
        pass
