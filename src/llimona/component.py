from abc import ABC
from logging import Logger, getLogger

from pydantic import BaseModel, Field

from llimona.utils import LoggerMixin


class ComponentDescription(BaseModel):
    type: str = Field(..., description='The type of the component')


class BaseComponent[TDesc: ComponentDescription](LoggerMixin, ABC):
    def __init__(self, desc: TDesc, *, logger: Logger | None = None) -> None:
        super().__init__(logger=logger or getLogger(f'llimona.component.{desc.type}'))
        self._desc = desc

    @property
    def desc(self) -> TDesc:
        return self._desc
