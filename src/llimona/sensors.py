import inspect
from abc import ABC, abstractmethod
from asyncio import get_event_loop
from collections.abc import AsyncGenerator, AsyncIterable, Awaitable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from functools import wraps
from logging import Logger, getLogger
from typing import Any, ClassVar, Literal, Self, cast, overload
from zoneinfo import ZoneInfo

from pydantic_extra_types.timezone_name import TimeZoneName

from llimona.component import BaseComponent, ComponentDescription
from llimona.context import Action, ActionIterable, ActionSingle, Context, SensorValue, SensorValueType
from llimona.models.common import BaseModel
from llimona.registries import ComponentDescriptionTypeMixin, ComponentRegistry


class ServiceAction(BaseModel):
    service: str
    action: str | None = None


class SensorApply(BaseModel):
    service_actions: list[ServiceAction] | None = None
    model: list[str] | None = None


class BaseSensorDesc(ComponentDescription):
    priority: int = 0
    name: str

    apply_to: list[SensorApply] | None = None


class BaseSensor[TModelDesc: BaseSensorDesc](BaseComponent[TModelDesc], ABC):
    def __init__(
        self,
        desc: TModelDesc,
        *,
        logger: Logger | None = None,
    ) -> None:
        super().__init__(
            desc=desc,
            logger=logger
            or getLogger(
                f'aicc_proxy.sensor.{desc.name}',
            ),
        )

    def _check_constraints(self, request: Context[Any], value: SensorValueType) -> None:
        for c in request.get_constraints(self.desc.name):
            if c.check(value):
                continue
            self._logger.debug(f'Constraint {c} not satisfied with value {value}.')
            raise ValueError(f'Constraint {c} not satisfied with value {value}.')

    @overload
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: ActionSingle[TRequest, TResponse, TArgs, TKwargs]
    ) -> ActionSingle[TRequest, TResponse, TArgs, TKwargs]: ...

    @overload
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: ActionIterable[TRequest, TResponse, TArgs, TKwargs]
    ) -> ActionIterable[TRequest, TResponse, TArgs, TKwargs]: ...

    @abstractmethod
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: Action[TRequest, TResponse, TArgs, TKwargs]
    ) -> Action[TRequest, TResponse, TArgs, TKwargs]:
        raise NotImplementedError()


type SensorRegistry = ComponentRegistry[BaseSensorDesc, BaseSensor]

sensor_registry: SensorRegistry = ComponentRegistry[BaseSensorDesc, BaseSensor](name='sensors')


class BaseSensorContext[TModel: BaseSensorDesc](BaseSensor[TModel], ABC):
    @overload
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: ActionSingle[TRequest, TResponse, TArgs, TKwargs]
    ) -> ActionSingle[TRequest, TResponse, TArgs, TKwargs]: ...

    @overload
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: ActionIterable[TRequest, TResponse, TArgs, TKwargs]
    ) -> ActionIterable[TRequest, TResponse, TArgs, TKwargs]: ...

    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: Action[TRequest, TResponse, TArgs, TKwargs]
    ) -> Action[TRequest, TResponse, TArgs, TKwargs]:
        if not inspect.isasyncgen(fn):

            @wraps(fn)
            async def wrapper(request: Context[TRequest], *args: TArgs, **kwargs: TKwargs) -> TResponse:  # pyright: ignore[reportRedeclaration]
                async with self.context(request, *args, **kwargs):
                    return await cast(Awaitable[TResponse], fn(request, *args, **kwargs))
        else:

            @wraps(fn)
            async def wrapper(request: Context[TRequest], *args: TArgs, **kwargs: TKwargs) -> AsyncIterable[TResponse]:
                need_exit = False
                ctx = self.context(request, *args, **kwargs)
                try:
                    await ctx.__aenter__()
                    need_exit = True
                except Exception as exc:  # pragma: no cover
                    self._logger.debug(f'Failed to enter sensor context: {exc}')

                try:
                    async for item in cast(AsyncIterable[TResponse], fn(request, *args, **kwargs)):
                        if need_exit:
                            await ctx.__aexit__(None, None, None)
                            need_exit = False
                        yield item
                except Exception as exc:
                    self._logger.debug(f'Failed to exit sensor context: {exc}')
                    if need_exit:
                        await ctx.__aexit__(type(exc), exc, exc.__traceback__)
                    raise

        return cast(Action[TRequest, TResponse, TArgs, TKwargs], wrapper)

    @abstractmethod
    def context[TRequest](self, request: Context[TRequest], *args: Any, **kwargs: Any) -> AbstractAsyncContextManager:
        raise NotImplementedError()


class RequestCountSensorDesc(BaseSensorDesc):
    type: Literal['request_count'] = 'request_count'  # type: ignore


class RequestCountSensor(BaseSensorContext[RequestCountSensorDesc]):
    _count: int = 0

    @asynccontextmanager
    async def context[TRequest](self, request: Context[TRequest], *args: Any, **kwargs: Any) -> AsyncGenerator[Self]:
        self._count += 1
        self._check_constraints(request, self._count)
        try:
            yield self
            request.add_sensor_value(
                SensorValue(
                    name=self._desc.name,
                    value=self._count,
                    description=f'Number of requests being processed for the sensor {self._desc.name}.',
                )
            )
        except BaseException as exc:
            self._count -= 1
            self._logger.debug(f'Request failed with error: {exc}. Total count: {self._count}')
            raise


sensor_registry.register_component(
    component_desc_cls=RequestCountSensorDesc,
    component_cls=RequestCountSensor,
)


class RequestPerUnitOfTimeSensorDesc(BaseSensorDesc):
    type: Literal['request_per_unit_of_time'] = 'request_per_unit_of_time'  # type: ignore

    unit_of_time: timedelta


class RequestPerUnitOfTimeSensor(BaseSensorContext[RequestPerUnitOfTimeSensorDesc]):
    class ExpireList:
        def __init__(self, unit_of_time: timedelta) -> None:
            self._items: list[datetime] = []
            self._next_cleanup: datetime | None = None
            self._unit_of_time = unit_of_time

        def append(self, item: datetime) -> int:
            self._items.append(item)
            return self.cleanup()

        def cleanup(self) -> int:
            now = datetime.now()

            if self._next_cleanup is not None and now < self._next_cleanup:
                return len(self._items)

            self._items = [r for r in self._items if now - r < self._unit_of_time]

            self._next_cleanup = self._items[0] + self._unit_of_time if self._items else None

            return len(self._items)

        def remove(self, item: datetime) -> int:
            self._items.remove(item)
            if self._next_cleanup is not None and item < self._next_cleanup:
                self._next_cleanup = None
            return self.cleanup()

    class RequestContext:
        def __init__(self, sensor: RequestPerUnitOfTimeSensor, dt: datetime, context: Context[Any]) -> None:
            self._sensor = sensor
            self._dt = dt
            self._context: Context[Any] = context

        async def __aenter__(self) -> Self:
            self._sensor._requests.append(self._dt)

            self._sensor._check_constraints(self._context, self._sensor._requests.cleanup())
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_val is None:
                assert self._context is not None

                self._sensor._logger.debug(
                    f'Request completed successfully. Request count on window: {self._sensor._requests.cleanup()}'
                )
                self._context.add_sensor_value(
                    SensorValue(
                        name=self._sensor._desc.name,
                        value=self._sensor._requests.cleanup(),
                        description=f'Number of requests in the last {self._sensor._desc.unit_of_time}.',
                    )
                )
            else:
                self._sensor._requests.remove(self._dt)
                self._sensor._logger.debug(
                    f'Request failed with error: {exc_val}. Request count on window: {self._sensor._requests.cleanup()}'
                )

    _requests: ExpireList

    def __init__(self, desc: RequestPerUnitOfTimeSensorDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc, logger=logger)

        self._requests = self.ExpireList(desc.unit_of_time)

    def context[TRequest](self, request: Context[TRequest], *args: Any, **kwargs: Any) -> AbstractAsyncContextManager:
        return self.RequestContext(self, datetime.now(), request)


sensor_registry.register_component(
    component_desc_cls=RequestPerUnitOfTimeSensorDesc,
    component_cls=RequestPerUnitOfTimeSensor,
)


class RequestPerWindowOfTimeSensorDesc(BaseSensorDesc):
    type: Literal['request_per_window_of_time'] = 'request_per_window_of_time'  # type: ignore

    cron_spec: str
    tz: TimeZoneName = TimeZoneName('UTC')


class RequestPerWindowOfTimeSensor(BaseSensorContext[RequestPerWindowOfTimeSensorDesc]):
    _count: int = 0

    def __init__(self, desc: RequestPerWindowOfTimeSensorDesc, *, logger: Logger | None = None) -> None:
        try:
            from cronsim import CronSim
        except ImportError as ex:  # pragma: no cover
            raise ImportError(
                "The 'cronsim' package is required to use the RequestPerWindowOfTimeSensor."
                " Please install it with 'pip install llimona[cron]'."
            ) from ex
        super().__init__(desc, logger=logger)

        self._cron_gen = CronSim(desc.cron_spec, datetime.now().astimezone(ZoneInfo(desc.tz)))
        self._next_reset = None

    def _reset(self):
        self._count = 0
        self._next_reset = None
        self._schedule_reset()

    def _schedule_reset(self):
        if self._next_reset is None:
            self._cron_gen.dt = datetime.now().replace(microsecond=0).astimezone(ZoneInfo(self._desc.tz))
            self._next_reset = get_event_loop().call_at(next(self._cron_gen).timestamp(), self._reset)

    def get_next_reset(self) -> datetime | None:
        return datetime.fromtimestamp(self._next_reset.when()) if self._next_reset is not None else None

    @asynccontextmanager
    async def context[TRequest](self, request: Context[TRequest], *args: Any, **kwargs: Any) -> AsyncGenerator[Self]:
        self._count += 1
        self._schedule_reset()
        try:
            self._check_constraints(request, self._count)
            yield self
            self._logger.debug(
                'Request completed successfully.'
                f' Request count until deadline: {self._count}. Next reset at: {self.get_next_reset()}'
            )
            request.add_sensor_value(
                SensorValue(
                    name=self._desc.name,
                    value=self._count,
                    description=f'Number of requests until the next reset at {self.get_next_reset()}.',
                )
            )
        except BaseException as exc:
            self._count -= 1
            self._logger.debug(
                f'Request failed with error: {exc}.'
                f' Request count until deadline: {self._count}. Next reset at: {self.get_next_reset()}'
            )
            raise


sensor_registry.register_component(
    component_desc_cls=RequestPerWindowOfTimeSensorDesc,
    component_cls=RequestPerWindowOfTimeSensor,
)


class ElapsedTimeSensorDesc(BaseSensorDesc):
    type: Literal['elapsed_time'] = 'elapsed_time'  # type: ignore


class ElapsedTimeSensor(BaseSensorContext[ElapsedTimeSensorDesc]):
    class RequestContext:
        def __init__(self, sensor: ElapsedTimeSensor, context: Context[Any]) -> None:
            self._sensor = sensor
            self._context = context
            self._start_time: datetime | None = None

        async def __aenter__(self):
            self._start_time = datetime.now().astimezone(UTC)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_val is not None:
                self._sensor._logger.debug(f'Request failed with error: {exc_val}. Elapsed time will not be recorded.')
                return

            assert self._start_time is not None

            elapsed = (datetime.now().astimezone(UTC) - self._start_time).total_seconds()
            self._sensor._logger.debug(f'Request completed successfully. Elapsed time: {elapsed:.2f}s.')
            self._context.add_sensor_value(
                SensorValue(
                    name=self._sensor._desc.name,
                    value=elapsed,
                    description='Elapsed time of the request.',
                )
            )

    def context[TRequest](self, request: Context[TRequest], *args: Any, **kwargs: Any) -> AbstractAsyncContextManager:
        return self.RequestContext(self, request)


sensor_registry.register_component(
    component_desc_cls=ElapsedTimeSensorDesc,
    component_cls=ElapsedTimeSensor,
)


class SensorType(ComponentDescriptionTypeMixin, BaseSensorDesc):
    registry: ClassVar[SensorRegistry] = sensor_registry
