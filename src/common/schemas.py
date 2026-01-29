from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

base_model_config = ConfigDict(
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

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = base_model_config


class BaseModelSchema(BaseModel):
    model_config = base_model_config


class Pagination(BaseModelSchema):
    count: int
    page: int
