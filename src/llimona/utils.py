from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from functools import wraps
from logging import Logger, getLogger
from typing import Concatenate


class LoggerMixin:
    def __init__(self, *, logger: Logger | None = None) -> None:
        self._logger = logger or getLogger(self.__class__.__name__)


class AsyncIterableMapper[TInput, TOutput](AsyncIterable[TOutput]):
    def __init__(self, iterable: AsyncIterable[TInput], first_mapper: Callable[[TInput], TOutput]) -> None:
        self._iterable = iterable
        self._first_mapper = first_mapper
        self._mappers: list[Callable[[TOutput], TOutput | Awaitable[TOutput]]] = []

    def add_mapper(self, mapper: Callable[[TOutput], TOutput | Awaitable[TOutput]]) -> None:
        self._mappers.append(mapper)

    async def __aiter__(self) -> AsyncIterator[TOutput]:
        async for item in self._iterable:
            output: TOutput = self._first_mapper(item)

            for mapper in self._mappers:
                result = mapper(output)
                if isinstance(result, Awaitable):
                    output = await result
                else:
                    output = result

            yield output


def log_exceptions[S: LoggerMixin, **MethParams, T](
    func: Callable[Concatenate[S, MethParams], T],
) -> Callable[Concatenate[S, MethParams], T]:
    @wraps(func)
    def wrap(
        self: S,
        *args: MethParams.args,
        **kwargs: MethParams.kwargs,
    ) -> T:
        silence = kwargs.pop('silence', False)
        try:
            return func(self, *args, **kwargs)
        except Exception as ex:
            if not silence:
                self._logger.error(ex)
            else:
                self._logger.debug(ex)
            raise

    return wrap
