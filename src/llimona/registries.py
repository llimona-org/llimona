from functools import lru_cache, reduce
from logging import Logger, getLogger
from types import UnionType
from typing import Annotated, Any, ClassVar, cast

from pydantic import BaseModel, Field, GetCoreSchemaHandler, TypeAdapter
from pydantic_core import CoreSchema

from llimona.component import BaseComponent, ComponentDescription
from llimona.utils import LoggerMixin


class ComponentRegistry[TDesc: ComponentDescription, TComp: BaseComponent[TDesc]](LoggerMixin):  # type: ignore
    def __init__(self, *, name: str = '', logger: Logger | None = None) -> None:
        super().__init__(logger=logger or getLogger(f'llimona.registry.{name}' if name else 'llimona.registry'))

        self._components: dict[str, tuple[type[TDesc], type[TComp]]] = {}

    def register_component(
        self,
        component_desc_cls: type[TDesc],
        component_cls: type[TComp],
    ) -> None:
        try:
            typ = component_desc_cls.model_fields['type'].default
        except KeyError:
            raise ValueError(
                f'Component description class {component_desc_cls} must have a "type" field with a default value'
            ) from None

        self._components[typ] = (
            component_desc_cls,
            component_cls,
        )

        self._logger.info(f'Registered component: {typ}')

        self.get_description_type_adapter.cache_clear()
        self.get_description_type.cache_clear()

    def get_description_class(self, typ: str) -> type[TDesc]:
        return self._components[typ][0]

    def get_component_class(self, typ: str) -> type[TComp]:
        return self._components[typ][1]  # pyright: ignore[reportReturnType]

    @lru_cache(maxsize=1)  # noqa: B019
    def get_description_type(self):
        if len(self._components) == 0:
            return None

        return Annotated[
            cast(
                UnionType,
                reduce(
                    lambda a, b: a | b,
                    (desc for desc, _ in self._components.values()),
                ),
            ),
            Field(discriminator='type'),
        ]

    @lru_cache(maxsize=1)  # noqa: B019
    def get_description_type_adapter(self) -> TypeAdapter[TDesc]:
        return TypeAdapter(self.get_description_type())

    def build(self, component_desc: TDesc) -> TComp:
        component_cls = self.get_component_class(component_desc.type)

        self._logger.info(f'Building component: {component_desc.type}')

        return component_cls(component_desc)


class ComponentDescriptionTypeMixin:
    registry: ClassVar[ComponentRegistry[Any, Any]]

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[BaseModel], handler: GetCoreSchemaHandler, /) -> CoreSchema:
        return handler(cls.registry.get_description_type_adapter().core_schema)
