from functools import wraps
from typing import Literal, cast, overload
from unittest import IsolatedAsyncioTestCase, TestCase

import pytest

from llimona.context import Action, ActionIterable, ActionSingle
from llimona.providers import (
    BaseProvider,
    BaseProviderDesc,
    BaseProviderModel,
    BaseProviderService,
    ProviderModelDesc,
    ProviderServiceDesc,
    check_uniqueness_model_name,
    check_uniqueness_sensor_name,
    check_uniqueness_service_type,
)
from llimona.sensors import BaseSensor, RequestCountSensorDesc, SensorApply, SensorType, ServiceAction


class ResponsesServiceDesc(ProviderServiceDesc):
    type: Literal['responses'] = 'responses'  # type: ignore


class EmbeddingsServiceDesc(ProviderServiceDesc):
    type: Literal['embeddings'] = 'embeddings'  # type: ignore


class DummyModelDesc(ProviderModelDesc):
    pass


class DummyProviderDesc(BaseProviderDesc):
    type: Literal['dummy'] = 'dummy'  # type: ignore


class DummyService(BaseProviderService):
    pass


class DummyModel(BaseProviderModel):
    pass


class DummyProvider(BaseProvider[DummyProviderDesc]):
    def __init__(self, desc: DummyProviderDesc) -> None:
        super().__init__(desc=desc)
        self.built_services: list[str] = []
        self.built_models: list[str] = []

    def _build_service(self, service: ProviderServiceDesc) -> BaseProviderService:
        self.built_services.append(service.type)
        return DummyService(provider=self, service=service)

    def _build_model(self, model: ProviderModelDesc) -> BaseProviderModel:
        self.built_models.append(model.name)
        return DummyModel(provider=self, desc=model)


class FakeSensor(BaseSensor[RequestCountSensorDesc]):
    def __init__(self, name: str, priority: int, *, apply_to: list[SensorApply] | None = None) -> None:
        super().__init__(desc=RequestCountSensorDesc(name=name, priority=priority, apply_to=apply_to))

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
        sensor_name = self.desc.name

        @wraps(fn)
        async def wrapped(*args, **kwargs):
            result = await cast(ActionSingle, fn)(*args, **kwargs)
            return cast(TResponse, f'{result}->{sensor_name}')

        return cast(Action[TRequest, TResponse, TArgs, TKwargs], wrapped)


def _build_provider(*, services=None, models=None, sensors=None) -> DummyProvider:
    provider = DummyProvider(
        DummyProviderDesc(
            name='provider-a',
            owner_id='owner-a',
            services=list(services or []),
            models=list(models or []),
        )
    )
    provider.sensors = list(sensors or [])
    return provider


class ProviderHelperTests(TestCase):
    def test_check_uniqueness_sensor_name_returns_sensors_when_names_are_unique(self):
        sensors = [
            cast(SensorType, RequestCountSensorDesc(name='sensor-a')),
            cast(SensorType, RequestCountSensorDesc(name='sensor-b')),
        ]

        result = check_uniqueness_sensor_name(sensors)

        assert result == sensors

    def test_check_uniqueness_sensor_name_raises_value_error_for_duplicate_names(self):
        sensors = [
            cast(SensorType, RequestCountSensorDesc(name='sensor-a')),
            cast(SensorType, RequestCountSensorDesc(name='sensor-a')),
        ]

        with pytest.raises(ValueError, match='Names are not unique'):
            check_uniqueness_sensor_name(sensors)

    def test_check_uniqueness_service_type_returns_services_when_types_are_unique(self):
        services = [ResponsesServiceDesc(), EmbeddingsServiceDesc()]

        result = check_uniqueness_service_type(services)

        assert result == services

    def test_check_uniqueness_service_type_raises_value_error_for_duplicate_types(self):
        services = [ResponsesServiceDesc(), ResponsesServiceDesc()]

        with pytest.raises(ValueError, match='Types are not unique'):
            check_uniqueness_service_type(services)

    def test_check_uniqueness_model_name_returns_models_when_names_are_unique(self):
        models = [DummyModelDesc(name='model-a'), DummyModelDesc(name='model-b')]

        result = check_uniqueness_model_name(models)

        assert result == models

    def test_check_uniqueness_model_name_raises_value_error_for_duplicate_names(self):
        models = [DummyModelDesc(name='model-a'), DummyModelDesc(name='model-a')]

        with pytest.raises(ValueError, match='Names are not unique'):
            check_uniqueness_model_name(models)


class BaseProviderTests(TestCase):
    def test_provider_property_returns_description(self):
        provider = _build_provider()

        assert provider.provider is provider.desc
        assert provider.provider.name == 'provider-a'

    def test_getattr_builds_service_and_caches_instance(self):
        provider = _build_provider(services=[ResponsesServiceDesc()])

        first_service = provider.responses
        second_service = provider.responses

        assert isinstance(first_service, DummyService)
        assert first_service is second_service
        assert provider.built_services == ['responses']

    def test_getattr_raises_attribute_error_when_service_not_found(self):
        provider = _build_provider(services=[ResponsesServiceDesc()])

        with pytest.raises(AttributeError, match="Service 'missing' not found"):
            _ = provider.missing

    def test_get_model_builds_model_and_caches_instance(self):
        provider = _build_provider(models=[DummyModelDesc(name='model-a')])

        first_model = provider.get_model('model-a')
        second_model = provider.get_model('model-a')

        assert isinstance(first_model, DummyModel)
        assert first_model is second_model
        assert provider.built_models == ['model-a']

    def test_get_model_raises_value_error_when_model_not_found(self):
        provider = _build_provider(models=[DummyModelDesc(name='model-a')])

        with pytest.raises(ValueError, match="Model 'model-b' not found"):
            provider.get_model('model-b')

    def test_get_sensors_filters_matches_and_sorts_by_priority(self):
        service_match = FakeSensor(
            'service-match',
            10,
            apply_to=[
                SensorApply(
                    service_actions=[ServiceAction(service='responses', action='create')],
                )
            ],
        )
        model_and_service = FakeSensor(
            'model-and-service',
            5,
            apply_to=[
                SensorApply(
                    service_actions=[ServiceAction(service='responses', action='create')],
                    model=['model-a'],
                )
            ],
        )
        global_sensor = FakeSensor('global', 1, apply_to=None)
        wrong_action = FakeSensor(
            'wrong-action',
            50,
            apply_to=[
                SensorApply(
                    service_actions=[ServiceAction(service='responses', action='delete')],
                )
            ],
        )

        provider = _build_provider(sensors=[global_sensor, wrong_action, model_and_service, service_match])

        sensors = provider.get_sensors('responses', 'create', 'model-a')

        assert sensors == [service_match, model_and_service, global_sensor]


class BaseProviderApplySensorsTests(IsolatedAsyncioTestCase):
    async def test_apply_sensors_wraps_function_in_sorted_order_and_caches_wrapper(self):
        high_priority = FakeSensor(
            'high-priority',
            10,
            apply_to=[
                SensorApply(
                    service_actions=[ServiceAction(service='responses', action='create')],
                )
            ],
        )
        low_priority = FakeSensor('low-priority', 1, apply_to=None)
        provider = _build_provider(sensors=[low_priority, high_priority])

        async def action() -> str:
            return 'base'

        first_wrapper = provider.apply_sensors(action, 'responses', 'create')
        second_wrapper = provider.apply_sensors(action, 'responses', 'create')

        result = await first_wrapper()

        assert first_wrapper is second_wrapper
        assert result == 'base->high-priority->low-priority'
