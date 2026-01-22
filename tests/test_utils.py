from collections.abc import AsyncIterable
from unittest import TestCase, mock

import pytest

from llimona.utils import AsyncIterableMapper, LoggerMixin, log_exceptions


async def _number_stream() -> AsyncIterable[int]:
    for item in [1, 2, 3]:
        yield item


class _Dummy(LoggerMixin):
    def __init__(self, logger: mock.Mock) -> None:
        super().__init__(logger=logger)

    @log_exceptions
    def add(self, left: int, right: int = 0) -> int:
        return left + right

    @log_exceptions
    def fail(self) -> None:
        raise ValueError('boom')

    @log_exceptions
    def echo(self, *, value: str) -> str:
        return value


class LogExceptionsDecoratorTests(TestCase):
    def test_log_exceptions_return_value(self):
        logger = mock.Mock()
        subject = _Dummy(logger=logger)

        result = subject.add(2, 3)

        assert result == 5
        logger.error.assert_not_called()
        logger.debug.assert_not_called()

    def test_log_exceptions_raise_and_log_error_by_default(self):
        logger = mock.Mock()
        subject = _Dummy(logger=logger)

        with pytest.raises(ValueError, match='boom'):
            subject.fail()

        logger.error.assert_called_once()
        logger.debug.assert_not_called()

    def test_log_exceptions_raise_and_log_debug_when_silence_true(self):
        logger = mock.Mock()
        subject = _Dummy(logger=logger)

        with pytest.raises(ValueError, match='boom'):
            subject.fail(silence=True)  # type: ignore

        logger.debug.assert_called_once()
        logger.error.assert_not_called()

    def test_log_exceptions_removes_silence_kwarg_before_call(self):
        logger = mock.Mock()
        subject = _Dummy(logger=logger)

        result = subject.echo(value='hello', silence=True)  # type: ignore

        assert result == 'hello'
        logger.error.assert_not_called()
        logger.debug.assert_not_called()


class TestAsyncIterableMapper:
    @pytest.mark.asyncio
    async def test_async_iterable_mapper_first_mapper_only(self):
        mapper = AsyncIterableMapper(_number_stream(), lambda x: x * 2)

        result = [item async for item in mapper]

        assert result == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_async_iterable_mapper_with_sync_mapper(self):
        mapper = AsyncIterableMapper(_number_stream(), lambda x: x * 2)
        mapper.add_mapper(lambda x: x + 1)

        result = [item async for item in mapper]

        assert result == [3, 5, 7]

    @pytest.mark.asyncio
    async def test_async_iterable_mapper_with_async_mapper(self):
        async def async_plus_one(value: int) -> int:
            return value + 1

        mapper = AsyncIterableMapper(_number_stream(), lambda x: x * 2)
        mapper.add_mapper(async_plus_one)

        result = [item async for item in mapper]

        assert result == [3, 5, 7]

    @pytest.mark.asyncio
    async def test_async_iterable_mapper_preserves_mapper_order(self):
        mapper = AsyncIterableMapper(_number_stream(), lambda x: x + 1)
        mapper.add_mapper(lambda x: x * 2)
        mapper.add_mapper(lambda x: x - 3)

        result = [item async for item in mapper]

        assert result == [1, 3, 5]
