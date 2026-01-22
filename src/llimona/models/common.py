from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel as PydanticBaseModel,
)
from pydantic import (
    ConfigDict,
    Field,
    SecretStr,
)
from pydantic.alias_generators import to_camel
from pydantic_views import (
    AccessMode,
    ReadOnly,
    ReadOnlyOnCreation,
    WriteOnly,
    WriteOnlyOnCreation,
)


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Entity(BaseModel):
    id: ReadOnly[str | None] = None

    created: ReadOnly[datetime] = Field(default_factory=datetime.now)
    modified: ReadOnly[datetime] = Field(default_factory=datetime.now)


class Named(BaseModel):
    name: WriteOnlyOnCreation[Annotated[str, AccessMode.READ_ONLY]]
    display_name: str | None = None


class NamedEntity(Entity, Named):
    pass


class Descripted(BaseModel):
    description: str | None = None


class Iconed(BaseModel):
    icon_url: str | None = None


class Owned(BaseModel):
    owner_id: str


class Secret(BaseModel):
    secret: ReadOnlyOnCreation[SecretStr | None] = None
    issued: ReadOnly[datetime] = Field(default_factory=datetime.now)
    expires: ReadOnly[datetime | None] = None


class GenericCredentials(BaseModel):
    api_key: WriteOnly[SecretStr]
    api_base: str | None = None
    api_version: str | None = None
