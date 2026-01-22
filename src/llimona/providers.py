from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, Awaitable, Callable, Sequence
from functools import lru_cache, reduce
from logging import Logger, getLogger
from typing import Annotated, ClassVar, Generic, Self, TypeVar, overload
from weakref import ref

from pydantic import AfterValidator, Field
from pydantic_views import AccessMode, ReadOnly

from llimona.component import BaseComponent, ComponentDescription
from llimona.interfaces.openai import Models as OpenAIModels
from llimona.interfaces.openai import Responses as OpenAIResponses
from llimona.models.common import BaseModel, Descripted, Iconed, NamedEntity, Owned
from llimona.registries import ComponentDescriptionTypeMixin, ComponentRegistry
from llimona.sensors import BaseSensor, BaseSensorDesc, SensorType
from llimona.utils import LoggerMixin


def check_uniqueness_sensor_name(sensors: list[SensorType]):
    names = [sensor.name for sensor in sensors]
    if len(names) != len(set(names)):
        raise ValueError(
            'Names are not unique. A provider cannot have more than one sensor with the same name.',
        )
    return sensors


class ProviderServiceDesc(BaseModel):
    type: ReadOnly[str]


class ProviderModelDesc(NamedEntity, Descripted):
    allowed_services: list[str] = Field(default_factory=list)


def check_uniqueness_service_type(services: Sequence[TProviderServiceDesc]):
    types = [service.type for service in services]
    if len(types) != len(set(types)):
        raise ValueError(
            'Types are not unique. A provider cannot have more than one service of the same type.',
        )
    return services


def check_uniqueness_model_name(models: Sequence[TProviderModelDesc]):
    names = [model.name for model in models]
    if len(names) != len(set(names)):
        raise ValueError(
            'Names are not unique. A provider cannot have more than one model with the same name.',
        )
    return models


TProviderModelDesc = TypeVar('TProviderModelDesc', bound=ProviderModelDesc, covariant=True)
TProviderServiceDesc = TypeVar('TProviderServiceDesc', bound=ProviderServiceDesc, covariant=True)


class BaseProviderDesc(
    NamedEntity,
    Iconed,
    Owned,
    Descripted,
    ComponentDescription,
    Generic[TProviderServiceDesc, TProviderModelDesc],  # noqa: UP046
):
    type: ReadOnly[str]

    services: Annotated[
        Sequence[TProviderServiceDesc],
        AfterValidator(check_uniqueness_service_type),
        AccessMode.READ_ONLY,
    ] = Field(default_factory=list)

    models: Annotated[
        Sequence[TProviderModelDesc],
        AfterValidator(check_uniqueness_model_name),
        AccessMode.READ_ONLY,
    ] = Field(default_factory=list)

    sensors: Annotated[  # type: ignore
        list[SensorType],
        AfterValidator(check_uniqueness_sensor_name),
        AccessMode.READ_ONLY,
    ] = Field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover
        if self.display_name:
            return f'{self.name} ({self.display_name} - {self.id})'
        return f'{self.name} ({self.id})'

    __repr__ = __str__


TBaseProviderDesc = TypeVar('TBaseProviderDesc', bound=BaseProviderDesc, covariant=True)
TProvider = TypeVar('TProvider', bound='BaseProvider', covariant=True)


class BaseProvider(BaseComponent[TBaseProviderDesc], ABC):
    openai_responses: OpenAIResponses
    openai_models: OpenAIModels

    def __init__(self, desc: TBaseProviderDesc, *, logger: Logger | None = None) -> None:
        super().__init__(
            desc=desc,
            logger=logger or getLogger(f'aicc_proxy.provider.{desc.name}'),
        )

        self._services: dict[str, BaseProviderService] = {}
        self._models: dict[str, BaseProviderModel] = {}

        self.sensors: list[BaseSensor] = []

    @property
    def provider(self) -> TBaseProviderDesc:
        return self._desc

    def __getattr__(self, name: str) -> BaseProviderService[Self]:
        try:
            return self._services[name]
        except KeyError:
            self._logger.debug(
                f"Service instance '{name}' not found. Building an instance '{name}'...",
            )
            try:
                service_model = next(s for s in self.provider.services if s.type == name)
            except StopIteration as ex:
                raise AttributeError(f"Service '{name}' not found") from ex

            service = self._build_service(service_model)
            self._services[name] = service
            return service

    def get_model(self, name: str) -> BaseProviderModel[Self, ProviderModelDesc]:
        try:
            return self._models[name]
        except KeyError:
            self._logger.debug(
                f"Model instance '{name}' not found. Building an instance '{name}'...",
            )
            try:
                model_desc = next(m for m in self.provider.models if m.name == name)
            except StopIteration as ex:
                raise ValueError(f"Model '{name}' not found") from ex

            model = self._build_model(model_desc)
            self._models[name] = model
            return model

    @abstractmethod
    def _build_service(self, service: ProviderServiceDesc) -> BaseProviderService[Self]:
        raise NotImplementedError()

    @abstractmethod
    def _build_model(self, model: ProviderModelDesc) -> BaseProviderModel[Self, ProviderModelDesc]:
        raise NotImplementedError()

    def get_sensors(self, service_type: str, action: str, model: str | None = None) -> list[BaseSensor]:
        lst: list[BaseSensor[BaseSensorDesc]] = [
            s
            for s in self.sensors
            if s._desc.apply_to is None
            or any(
                (
                    am.service_actions is None
                    or any(
                        sa.service == service_type and (sa.action is None or sa.action == action)
                        for sa in am.service_actions
                    )
                )
                and (am.model is None or model in am.model)
                for am in s._desc.apply_to
            )
        ]

        lst.sort(key=lambda w: w.desc.priority, reverse=True)
        return lst

    @overload
    def apply_sensors[**Params, O](
        self, fn: Callable[Params, Awaitable[O]], service_type: str, action: str, model: str | None = None
    ) -> Callable[Params, Awaitable[O]]: ...

    @overload
    def apply_sensors[**Params, O](
        self, fn: Callable[Params, AsyncIterable[O]], service_type: str, action: str, model: str | None = None
    ) -> Callable[Params, AsyncIterable[O]]: ...

    @lru_cache(maxsize=128)  # noqa: B019
    def apply_sensors[**Params, O](
        self,
        fn: Callable[Params, Awaitable[O] | AsyncIterable[O]],
        service_type: str,
        action: str,
        model: str | None = None,
    ) -> Callable[Params, Awaitable[O] | AsyncIterable[O]]:
        sensors = self.get_sensors(service_type, action, model)
        return reduce(lambda f, sensor: sensor(f), sensors, fn)  # type: ignore


type ProviderRegistry = ComponentRegistry[BaseProviderDesc, BaseProvider]

provider_registry: ProviderRegistry = ComponentRegistry[BaseProviderDesc, BaseProvider](name='providers')


class ProviderType(ComponentDescriptionTypeMixin, BaseProviderDesc):
    registry: ClassVar[ProviderRegistry] = provider_registry


class BaseProviderOwned(Generic[TProvider], ABC, LoggerMixin):  # noqa: UP046
    def __init__(
        self,
        provider: TProvider,
        *,
        logger: Logger | None = None,
    ) -> None:
        super().__init__(logger=logger)
        self._provider = ref(provider)

    @property
    def provider(self) -> TProvider:
        provider = self._provider()
        if provider is None:
            raise ReferenceError('The provider reference is no longer valid')
        return provider


class BaseProviderService(BaseProviderOwned[TProvider], ABC):
    TYPE: ClassVar[str]

    def __init__(
        self,
        provider: TProvider,
        service: ProviderServiceDesc,
        *,
        logger: Logger | None = None,
    ) -> None:
        super().__init__(
            provider=provider,
            logger=logger
            or getLogger(
                f'aicc_proxy.provider.{provider.provider.name}.{service.type}',
            ),
        )

        self.service = service


class BaseProviderModel(BaseProviderOwned[TProvider], Generic[TProvider, TProviderModelDesc], ABC):  # noqa: UP046
    def __init__(
        self,
        provider: TProvider,
        desc: TProviderModelDesc,
        *,
        logger: Logger | None = None,
    ) -> None:
        super().__init__(
            provider=provider,
            logger=logger
            or getLogger(
                f'aicc_proxy.provider.{provider.provider.name}.model.{desc.name}',
            ),
        )

        self.desc = desc
