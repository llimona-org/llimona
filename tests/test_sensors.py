import sys
import types
from datetime import UTC, datetime, timedelta
from unittest import IsolatedAsyncioTestCase, mock

import pytest

from llimona.sensors import (
    ElapsedTimeSensor,
    ElapsedTimeSensorDesc,
    RequestCountSensor,
    RequestCountSensorDesc,
    RequestPerUnitOfTimeSensor,
    RequestPerUnitOfTimeSensorDesc,
    RequestPerWindowOfTimeSensor,
    RequestPerWindowOfTimeSensorDesc,
)


def _request_mock() -> mock.Mock:
    request = mock.Mock()
    request.get_constraints.return_value = []
    return request


def _unsatisfied_constraint() -> mock.Mock:
    constraint = mock.Mock()
    constraint.check.return_value = False
    setattr(constraint, '__str__', mock.Mock(return_value='constraint-1'))  # noqa: B010
    return constraint


def _satisfied_constraint() -> mock.Mock:
    constraint = mock.Mock()
    constraint.check.return_value = True
    setattr(constraint, '__str__', mock.Mock(return_value='constraint-ok'))  # noqa: B010
    return constraint


class RequestCountSensorTests(IsolatedAsyncioTestCase):
    async def test_context_adds_sensor_value_on_success(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()

        async with sensor.context(request):
            pass

        request.add_sensor_value.assert_called_once()
        sensor_value = request.add_sensor_value.call_args.args[0]
        assert sensor_value.name == 'request-count'
        assert sensor_value.value == 1

    async def test_context_decrements_count_on_exception(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()

        with pytest.raises(RuntimeError, match='boom'):
            async with sensor.context(request):
                raise RuntimeError('boom')

        request.add_sensor_value.assert_not_called()
        assert sensor._count == 0

    async def test_context_raises_value_error_when_constraint_is_not_satisfied(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()
        constraint = _unsatisfied_constraint()
        request.get_constraints.return_value = [constraint]

        with pytest.raises(ValueError, match='Constraint'):
            async with sensor.context(request):
                pass

        request.add_sensor_value.assert_not_called()
        constraint.check.assert_called_once_with(1)
        sensor._count = 0

    async def test_context_does_not_fail_when_all_constraints_are_satisfied(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()
        constraints = [_satisfied_constraint(), _satisfied_constraint()]
        request.get_constraints.return_value = constraints

        async with sensor.context(request):
            pass

        request.add_sensor_value.assert_called_once()
        for constraint in constraints:
            constraint.check.assert_called_once_with(1)

    async def test_call_wraps_async_function_and_records_sensor_value(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()

        async def action(ctx):
            return f'ok:{ctx is request}'

        wrapped_action = sensor(action)  # type: ignore
        result = await wrapped_action(request)

        assert result == 'ok:True'
        request.add_sensor_value.assert_called_once()
        sensor_value = request.add_sensor_value.call_args.args[0]
        assert sensor_value.name == 'request-count'
        assert sensor_value.value == 1

    async def test_call_wraps_async_generator_and_exits_context_before_first_item(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()

        async def action_stream(_ctx):
            yield 'first'
            yield 'second'

        with mock.patch('llimona.sensors.inspect.isasyncgen', return_value=True):
            wrapped_action = sensor(action_stream)  # type: ignore
            result = [item async for item in wrapped_action(request)]

        assert result == ['first', 'second']
        request.add_sensor_value.assert_called_once()
        sensor_value = request.add_sensor_value.call_args.args[0]
        assert sensor_value.name == 'request-count'
        assert sensor_value.value == 1

    async def test_call_wraps_async_generator_and_propagates_error(self):
        sensor = RequestCountSensor(RequestCountSensorDesc(name='request-count'))
        request = _request_mock()

        async def action_stream(_ctx):
            raise RuntimeError('stream-error')
            yield 'never'

        with mock.patch('llimona.sensors.inspect.isasyncgen', return_value=True):
            wrapped_action = sensor(action_stream)  # type: ignore

            with pytest.raises(RuntimeError, match='stream-error'):
                _ = [item async for item in wrapped_action(request)]

        request.add_sensor_value.assert_not_called()
        assert sensor._count == 0


class RequestPerUnitOfTimeSensorTests(IsolatedAsyncioTestCase):
    async def test_context_adds_sensor_value_on_success(self):
        sensor = RequestPerUnitOfTimeSensor(
            RequestPerUnitOfTimeSensorDesc(name='request-window', unit_of_time=timedelta(seconds=60))
        )
        request = _request_mock()

        async with sensor.context(request):
            pass

        request.add_sensor_value.assert_called_once()
        sensor_value = request.add_sensor_value.call_args.args[0]
        assert sensor_value.name == 'request-window'
        assert isinstance(sensor_value.value, int)
        assert sensor_value.value >= 1

    async def test_context_removes_request_on_exception(self):
        sensor = RequestPerUnitOfTimeSensor(
            RequestPerUnitOfTimeSensorDesc(name='request-window', unit_of_time=timedelta(seconds=60))
        )
        request = _request_mock()

        with pytest.raises(ValueError, match='failed'):
            async with sensor.context(request):
                raise ValueError('failed')

        request.add_sensor_value.assert_not_called()
        assert sensor._requests.cleanup() == 0

    async def test_context_raises_value_error_when_constraint_is_not_satisfied(self):
        sensor = RequestPerUnitOfTimeSensor(
            RequestPerUnitOfTimeSensorDesc(name='request-window', unit_of_time=timedelta(seconds=60))
        )
        request = _request_mock()
        constraint = _unsatisfied_constraint()
        request.get_constraints.return_value = [constraint]

        with pytest.raises(ValueError, match='Constraint'):
            async with sensor.context(request):
                pass

        request.add_sensor_value.assert_not_called()
        constraint.check.assert_called_once_with(1)

    async def test_context_does_not_fail_when_all_constraints_are_satisfied(self):
        sensor = RequestPerUnitOfTimeSensor(
            RequestPerUnitOfTimeSensorDesc(name='request-window', unit_of_time=timedelta(seconds=60))
        )
        request = _request_mock()
        constraints = [_satisfied_constraint(), _satisfied_constraint()]
        request.get_constraints.return_value = constraints

        async with sensor.context(request):
            pass

        request.add_sensor_value.assert_called_once()
        for constraint in constraints:
            constraint.check.assert_called_once_with(1)


class RequestPerWindowOfTimeSensorTests(IsolatedAsyncioTestCase):
    async def test_schedule_reset_sets_next_reset_only_once(self):
        class FakeCronSim:
            def __init__(self, spec: str, dt: datetime) -> None:
                self.spec = spec
                self.dt = dt

            def __iter__(self):
                return self

            def __next__(self) -> datetime:
                return self.dt + timedelta(minutes=1)

        handle = mock.Mock()
        handle.when.return_value = (datetime.now().astimezone(UTC) + timedelta(minutes=1)).timestamp()
        loop = mock.Mock()
        loop.call_at.return_value = handle

        with (
            mock.patch.dict(sys.modules, {'cronsim': types.SimpleNamespace(CronSim=FakeCronSim)}),
            mock.patch('llimona.sensors.get_event_loop', return_value=loop),
        ):
            sensor = RequestPerWindowOfTimeSensor(
                RequestPerWindowOfTimeSensorDesc(name='request-cron', cron_spec='* * * * *')
            )

            sensor._schedule_reset()
            first_next_reset = sensor._next_reset

            sensor._schedule_reset()

        assert first_next_reset is not None
        assert sensor._next_reset is first_next_reset
        loop.call_at.assert_called_once()

    async def test_reset_clears_count_and_reschedules(self):
        class FakeCronSim:
            def __init__(self, spec: str, dt: datetime) -> None:
                self.spec = spec
                self.dt = dt

            def __iter__(self):
                return self

            def __next__(self) -> datetime:
                return self.dt + timedelta(minutes=1)

        with mock.patch.dict(sys.modules, {'cronsim': types.SimpleNamespace(CronSim=FakeCronSim)}):
            sensor = RequestPerWindowOfTimeSensor(
                RequestPerWindowOfTimeSensorDesc(name='request-cron', cron_spec='* * * * *')
            )

        sensor._count = 7
        sensor._next_reset = mock.Mock()

        with mock.patch.object(sensor, '_schedule_reset') as schedule_reset:
            sensor._reset()

        assert sensor._count == 0
        assert sensor._next_reset is None
        schedule_reset.assert_called_once_with()

    async def test_context_adds_sensor_value_on_success(self):
        class FakeCronSim:
            def __init__(self, spec: str, dt: datetime) -> None:
                self.spec = spec
                self.dt = dt

            def __iter__(self):
                return self

            def __next__(self) -> datetime:
                return self.dt + timedelta(minutes=1)

        handle = mock.Mock()
        handle.when.return_value = (datetime.now().astimezone(UTC) + timedelta(minutes=1)).timestamp()
        loop = mock.Mock()
        loop.call_at.return_value = handle

        request = _request_mock()

        with (
            mock.patch.dict(sys.modules, {'cronsim': types.SimpleNamespace(CronSim=FakeCronSim)}),
            mock.patch('llimona.sensors.get_event_loop', return_value=loop),
        ):
            sensor = RequestPerWindowOfTimeSensor(
                RequestPerWindowOfTimeSensorDesc(name='request-cron', cron_spec='* * * * *')
            )

            async with sensor.context(request):
                pass

        request.add_sensor_value.assert_called_once()
        sensor_value = request.add_sensor_value.call_args.args[0]
        assert sensor_value.name == 'request-cron'
        assert sensor_value.value == 1
        loop.call_at.assert_called_once()
        assert sensor.get_next_reset() is not None

    async def test_context_decrements_count_on_exception(self):
        class FakeCronSim:
            def __init__(self, spec: str, dt: datetime) -> None:
                self.spec = spec
                self.dt = dt

            def __iter__(self):
                return self

            def __next__(self) -> datetime:
                return self.dt + timedelta(minutes=1)

        handle = mock.Mock()
        handle.when.return_value = (datetime.now().astimezone(UTC) + timedelta(minutes=1)).timestamp()
        loop = mock.Mock()
        loop.call_at.return_value = handle

        request = _request_mock()

        with (
            mock.patch.dict(sys.modules, {'cronsim': types.SimpleNamespace(CronSim=FakeCronSim)}),
            mock.patch('llimona.sensors.get_event_loop', return_value=loop),
        ):
            sensor = RequestPerWindowOfTimeSensor(
                RequestPerWindowOfTimeSensorDesc(name='request-cron', cron_spec='* * * * *')
            )

            with pytest.raises(RuntimeError, match='failed'):
                async with sensor.context(request):
                    raise RuntimeError('failed')

        request.add_sensor_value.assert_not_called()
        assert sensor._count == 0

    async def test_context_raises_value_error_when_constraint_is_not_satisfied(self):
        class FakeCronSim:
            def __init__(self, spec: str, dt: datetime) -> None:
                self.spec = spec
                self.dt = dt

            def __iter__(self):
                return self

            def __next__(self) -> datetime:
                return self.dt + timedelta(minutes=1)

        handle = mock.Mock()
        handle.when.return_value = (datetime.now().astimezone(UTC) + timedelta(minutes=1)).timestamp()
        loop = mock.Mock()
        loop.call_at.return_value = handle

        request = _request_mock()
        constraint = _unsatisfied_constraint()
        request.get_constraints.return_value = [constraint]

        with (
            mock.patch.dict(sys.modules, {'cronsim': types.SimpleNamespace(CronSim=FakeCronSim)}),
            mock.patch('llimona.sensors.get_event_loop', return_value=loop),
        ):
            sensor = RequestPerWindowOfTimeSensor(
                RequestPerWindowOfTimeSensorDesc(name='request-cron', cron_spec='* * * * *')
            )

            with pytest.raises(ValueError, match='Constraint'):
                async with sensor.context(request):
                    pass

        request.add_sensor_value.assert_not_called()
        constraint.check.assert_called_once_with(1)
        assert sensor._count == 0

    async def test_context_does_not_fail_when_all_constraints_are_satisfied(self):
        class FakeCronSim:
            def __init__(self, spec: str, dt: datetime) -> None:
                self.spec = spec
                self.dt = dt

            def __iter__(self):
                return self

            def __next__(self) -> datetime:
                return self.dt + timedelta(minutes=1)

        handle = mock.Mock()
        handle.when.return_value = (datetime.now().astimezone(UTC) + timedelta(minutes=1)).timestamp()
        loop = mock.Mock()
        loop.call_at.return_value = handle

        request = _request_mock()
        constraints = [_satisfied_constraint(), _satisfied_constraint()]
        request.get_constraints.return_value = constraints

        with (
            mock.patch.dict(sys.modules, {'cronsim': types.SimpleNamespace(CronSim=FakeCronSim)}),
            mock.patch('llimona.sensors.get_event_loop', return_value=loop),
        ):
            sensor = RequestPerWindowOfTimeSensor(
                RequestPerWindowOfTimeSensorDesc(name='request-cron', cron_spec='* * * * *')
            )

            async with sensor.context(request):
                pass

        request.add_sensor_value.assert_called_once()
        for constraint in constraints:
            constraint.check.assert_called_once_with(1)


class ElapsedTimeSensorTests(IsolatedAsyncioTestCase):
    async def test_context_adds_sensor_value_on_success(self):
        sensor = ElapsedTimeSensor(ElapsedTimeSensorDesc(name='elapsed-time'))
        request = _request_mock()

        async with sensor.context(request):
            pass

        request.add_sensor_value.assert_called_once()
        sensor_value = request.add_sensor_value.call_args.args[0]
        assert sensor_value.name == 'elapsed-time'
        assert isinstance(sensor_value.value, float)
        assert sensor_value.value >= 0

    async def test_context_does_not_add_sensor_value_on_exception(self):
        sensor = ElapsedTimeSensor(ElapsedTimeSensorDesc(name='elapsed-time'))
        request = _request_mock()

        with pytest.raises(ValueError, match='error'):
            async with sensor.context(request):
                raise ValueError('error')

        request.add_sensor_value.assert_not_called()
