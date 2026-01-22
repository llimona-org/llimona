from collections.abc import AsyncIterable, Awaitable, Iterable, Iterator, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol, Self
from weakref import ref

from pydantic import ConfigDict, Field, IPvAnyAddress

from llimona.app import Llimona
from llimona.models.common import BaseModel


class Actor(BaseModel):
    class Type(StrEnum):
        USER = 'user'
        API_KEY = 'api_key'

    id: str
    scopes: set[str] = Field(default_factory=set)
    display_name: str | None = None
    description: str | None = None
    type: Type = Type.USER


class Origin(BaseModel):
    correlation_id: str
    origin: IPvAnyAddress | None = None
    origin_port: int | None = None
    user_agent: str | None = None


class Interlocutor(BaseModel):
    id: str
    display_name: str | None = None
    description: str | None = None


class Conversation(BaseModel):
    class MediaType(StrEnum):
        TEXT = 'text'
        IMAGE = 'image'
        AUDIO = 'audio'
        VIDEO = 'video'

    id: str
    interlocutors: list[Interlocutor] = Field(default_factory=list)
    media: MediaType = MediaType.TEXT


SensorValueType = str | int | float | bool | datetime | timedelta


class SensorValue(BaseModel):
    model_config = ConfigDict(extra='allow')

    name: str
    value: SensorValueType | list[SensorValueType] | dict[str, SensorValueType]
    description: str | None = None


class ActionSingle[TRequest, TResponse, TArgs, TKwargs](Protocol):
    def __call__(
        self,
        request: Context[TRequest],
        *args: TArgs,
        **kwargs: TKwargs,
    ) -> Awaitable[TResponse]: ...


class ActionIterable[TRequest, TResponse, TArgs, TKwargs](Protocol):
    def __call__(
        self,
        request: Context[TRequest],
        *args: TArgs,
        **kwargs: TKwargs,
    ) -> AsyncIterable[TResponse]: ...


type Action[TRequest, TResponse, TArgs, TKwargs] = (
    ActionSingle[TRequest, TResponse, TArgs, TKwargs] | ActionIterable[TRequest, TResponse, TArgs, TKwargs]
)


class ActionContext(BaseModel):
    model_config = ConfigDict(extra='allow')

    provider: str
    service: str
    service_action: str
    model: str | None = None


class Constraint(BaseModel):
    class Operator(StrEnum):
        EQUALS = 'equals'
        NOT_EQUALS = 'not_equals'
        GREATER_THAN = 'greater_than'
        LESS_THAN = 'less_than'
        IN = 'in'
        NOT_IN = 'not_in'

    model_config = ConfigDict(extra='allow')

    provider: str
    sensor: str
    metric: str | None = None
    operator: Operator
    value: SensorValueType | list[SensorValueType] | dict[str, SensorValueType]

    def check(self, sensor_value: SensorValueType) -> bool:
        match self.operator:
            case self.Operator.EQUALS:
                return sensor_value == self.value
            case self.Operator.NOT_EQUALS:
                return sensor_value != self.value
            case self.Operator.GREATER_THAN:
                if not isinstance(sensor_value, (int, float)):
                    raise ValueError(f'GREATER_THAN operator requires numeric sensor value, got {type(sensor_value)}')
                if not isinstance(self.value, (int, float)):
                    raise ValueError(f'GREATER_THAN operator requires numeric constraint value, got {type(self.value)}')
                return sensor_value > self.value
            case self.Operator.LESS_THAN:
                if not isinstance(sensor_value, (int, float)):
                    raise ValueError(f'LESS_THAN operator requires numeric sensor value, got {type(sensor_value)}')
                if not isinstance(self.value, (int, float)):
                    raise ValueError(f'LESS_THAN operator requires numeric constraint value, got {type(self.value)}')
                return sensor_value < self.value
            case self.Operator.IN:
                if not isinstance(self.value, (list, dict)):
                    raise ValueError(f'IN operator requires list or dict constraint value, got {type(self.value)}')
                return sensor_value in self.value
            case self.Operator.NOT_IN:
                if not isinstance(self.value, (list, dict)):
                    raise ValueError(f'NOT_IN operator requires list or dict constraint value, got {type(self.value)}')
                return sensor_value not in self.value
            case _:
                raise ValueError(f'Unsupported operator: {self.operator}')


class Context[TRequest]:
    def __init__(
        self,
        app: Llimona,
        request: TRequest,
        *,
        action: ActionContext | None = None,
        origin: Origin | None = None,
        actor: Actor | None = None,
        conversation: Conversation | None = None,
        constraints: Sequence[Constraint] | None = None,
        parent: Context | None = None,
    ) -> None:
        self._app = app
        self._action = action
        self._request = request
        self._origin = origin
        self._actor = actor
        self._conversation = conversation
        self._parent = ref(parent) if parent is not None else None
        self._constraints = list(constraints) if constraints is not None else []

        self._sensor_values: list[SensorValue] = []
        self._subcontexts: list[Context] = []
        self._exception: BaseException | None = None

        self._metadata: dict[str, Any] = {}

    @property
    def app(self) -> Llimona:
        return self._app

    @property
    def request(self) -> TRequest:
        return self._request

    @property
    def origin(self) -> Origin | None:
        return self._origin

    @property
    def actor(self) -> Actor | None:
        return self._actor

    @property
    def conversation(self) -> Conversation | None:
        return self._conversation

    @property
    def action(self) -> ActionContext | None:
        return self._action

    @property
    def parent(self) -> Context | None:
        return self._parent() if self._parent is not None else None

    def get_sensor_values(self, only_success: bool = True) -> Iterator[SensorValue]:
        yield from self._sensor_values
        for subctx in self._subcontexts:
            if only_success and subctx.is_failed():
                continue
            yield from subctx.get_sensor_values(only_success=only_success)

    def add_sensor_value(self, sensor_value: SensorValue) -> None:
        self._sensor_values.append(sensor_value)

    def create_subcontext[T](
        self,
        action: ActionContext,
        request: T,
        *,
        conversation: Conversation | None = None,
        origin: Origin | None = None,
        actor: Actor | None = None,
        constraints: Sequence[Constraint] | None = None,
    ) -> Context[T]:
        subctx = Context(
            app=self._app,
            action=action,
            request=request,
            origin=origin or self._origin,
            actor=actor or self._actor,
            conversation=conversation or self._conversation,
            constraints=constraints,
            parent=self,
        )
        self._subcontexts.append(subctx)

        return subctx

    def get_subcontexts(self, only_success: bool = True) -> Iterable[Context]:
        for subctx in self._subcontexts:
            if only_success and subctx.is_failed():
                continue
            yield subctx

    def get_constraints(self, sensor: str) -> Iterable[Constraint]:
        yield from (
            constraint
            for constraint in self._constraints
            if constraint.sensor == sensor and self._action is not None and constraint.provider == self._action.provider
        )
        yield from self.parent.get_constraints(sensor) if self.parent is not None else ()

    def set_exception(self, exception: BaseException) -> None:
        self._exception = exception

    def is_failed(self) -> bool:
        return self._exception is not None

    def get_exception(self) -> BaseException | None:
        return self._exception

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.set_exception(exc_val)

    def get_metadata[T](self, typ: type[T], name: str | None = None) -> tuple[str, T]:
        try:
            return next(
                (key, value)
                for key, value in self._metadata.items()
                if isinstance(value, typ) and (name is None or key == name)
            )
        except StopIteration:
            pass

        if self.parent is not None:
            key, value = self.parent.get_metadata(typ, name=name)
            return key, value

        if name is not None:
            raise ValueError(f'Metadata of type {typ} with name "{name}" not found in context hierarchy')
        raise ValueError(f'Metadata of type {typ} not found in context hierarchy')

    def set_metadata(self, name: str, value: Any) -> None:
        self._metadata[name] = value
