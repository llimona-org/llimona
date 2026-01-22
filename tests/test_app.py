import gc
from datetime import UTC, datetime
from unittest import IsolatedAsyncioTestCase, TestCase, mock

import pytest

from llimona.app import Llimona, OpenAIModels, OpenAIResponses
from llimona.context import ActionContext
from llimona.id_builders import PlainIdBuilder, PlainIdBuilderDesc
from llimona.interfaces.openai.models.api_models import Model
from llimona.interfaces.openai.models.api_responses import (
    CreateResponse,
    DeleteResponse,
    RetrieveResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_provider(name='provider-a', owner_id='owner-1', services=None, models=None):
    p = mock.Mock()
    p.provider.name = name
    p.provider.owner_id = owner_id
    p.provider.services = services or []
    p.provider.models = models or []
    return p


def _make_app(*providers):
    if not providers:
        providers = [_make_mock_provider()]
    return Llimona(providers=providers)


def _make_model_desc(name='model-1', created_ts=1_700_000_000):
    m = mock.Mock()
    m.name = name
    m.created = datetime.fromtimestamp(created_ts, tz=UTC)
    return m


def _make_api_model(model_id='model-1'):
    return Model(id=model_id, created=1_700_000_000, owned_by='owner-1')


def _make_id_builder_mock(provider_name='provider-a', actor_id=None, resp_id='raw-resp-id'):
    b = mock.Mock()
    b.debuild_response_id = mock.AsyncMock(return_value=(provider_name, actor_id, resp_id))
    b.build_response_id = mock.AsyncMock(return_value='remapped-id')
    return b


# ---------------------------------------------------------------------------
# Llimona init tests
# ---------------------------------------------------------------------------


class LlimonaInitTests(TestCase):
    def test_providers_accessible_by_name(self):
        provider = _make_mock_provider('my-provider')
        app = Llimona(providers=[provider])

        assert app.get_provider('my-provider') is provider

    def test_openai_responses_attribute_is_openai_responses_instance(self):
        app = _make_app()

        assert isinstance(app.openai_responses, OpenAIResponses)

    def test_openai_models_attribute_is_openai_models_instance(self):
        app = _make_app()

        assert isinstance(app.openai_models, OpenAIModels)

    def test_default_id_builder_is_plain_id_builder(self):
        app = _make_app()

        assert isinstance(app.id_builder, PlainIdBuilder)

    def test_custom_id_builder_is_used_when_provided(self):
        builder = PlainIdBuilder(desc=PlainIdBuilderDesc())
        app = Llimona(providers=[], id_builder=builder)

        assert app.id_builder is builder


# ---------------------------------------------------------------------------
# Llimona method tests
# ---------------------------------------------------------------------------


class LlimonaMethodTests(TestCase):
    def test_decompose_model_splits_by_slash(self):
        app = _make_app()

        assert app.decompose_model('provider/model-name') == ('provider', 'model-name')

    def test_get_provider_returns_registered_provider(self):
        p = _make_mock_provider('prov')
        app = Llimona(providers=[p])

        assert app.get_provider('prov') is p

    def test_get_provider_raises_key_error_for_unknown_name(self):
        app = _make_app()

        with pytest.raises(KeyError):
            app.get_provider('unknown')

    def test_register_provider_makes_it_accessible(self):
        app = _make_app()
        p = _make_mock_provider('new-provider')

        app.register_provider(p)

        assert app.get_provider('new-provider') is p

    def test_register_provider_raises_assertion_for_duplicate_name(self):
        p = _make_mock_provider('prov')
        app = Llimona(providers=[p])
        duplicate = _make_mock_provider('prov')

        with pytest.raises(AssertionError):
            app.register_provider(duplicate)

    def test_build_context_returns_context_with_correct_app_and_request(self):
        app = _make_app()

        ctx = app.build_context('my-request')

        assert ctx.app is app
        assert ctx.request == 'my-request'


class LlimonaValidateActorTests(IsolatedAsyncioTestCase):
    async def test_validate_actor_passes_when_ids_match(self):
        app = _make_app()

        await app.validate_actor('actor-1', 'actor-1')  # no exception

    async def test_validate_actor_passes_when_both_none(self):
        app = _make_app()

        await app.validate_actor(None, None)  # no exception

    async def test_validate_actor_raises_when_ids_differ(self):
        app = _make_app()

        with pytest.raises(ValueError, match='Actor ID does not match'):
            await app.validate_actor('actor-a', 'actor-b')


# ---------------------------------------------------------------------------
# BaseService tests (via OpenAIResponses as concrete class)
# ---------------------------------------------------------------------------


class BaseServiceAppPropertyTests(TestCase):
    def test_app_property_returns_associated_app(self):
        app = _make_app()

        assert app.openai_responses.app is app

    def test_app_property_raises_reference_error_after_app_is_garbage_collected(self):
        app = _make_app()
        svc = app.openai_responses
        del app
        gc.collect()

        with pytest.raises(ReferenceError):
            _ = svc.app


class BaseServiceBuildContextTests(TestCase):
    def test_standalone_context_has_correct_action_fields(self):
        app = _make_app()

        ctx = app.openai_responses._build_context(
            request='req',
            provider='provider-a',
            service_action='create',
            model='model-1',
        )

        assert ctx.request == 'req'
        assert ctx.action is not None
        assert ctx.action.provider == 'provider-a'
        assert ctx.action.service == 'openai_responses'
        assert ctx.action.service_action == 'create'
        assert ctx.action.model == 'model-1'

    def test_context_with_parent_creates_subcontext(self):
        app = _make_app()
        parent = app.build_context(
            'parent-req',
            action=ActionContext(provider='provider-a', service='s', service_action='a'),
        )

        sub = app.openai_responses._build_context(
            request='sub-req',
            provider='provider-a',
            service_action='create',
            parent_ctx=parent,
        )

        assert sub.parent is parent
        assert sub.request == 'sub-req'

    def test_context_raises_when_parent_belongs_to_different_app(self):
        app1 = _make_app()
        app2 = _make_app()
        parent = app2.build_context('req')

        with pytest.raises(ValueError, match='different app'):
            app1.openai_responses._build_context(
                request='req',
                provider='provider-a',
                service_action='create',
                parent_ctx=parent,
            )


# ---------------------------------------------------------------------------
# OpenAIResponses tests
# ---------------------------------------------------------------------------


class OpenAIResponsesCreateTests(IsolatedAsyncioTestCase):
    async def test_create_calls_provider_and_returns_mapped_response(self):
        fake_response = mock.Mock()
        fake_response.id = 'resp-1'
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=fake_response)
        app = Llimona(providers=[provider])

        with mock.patch('llimona.interfaces.openai.mappers.IdMapper') as MockIdMapper:  # noqa: N806
            mapped = mock.Mock()
            MockIdMapper.return_value.map_raw_response = mock.AsyncMock(return_value=mapped)

            request = CreateResponse(model='prov-a/model-1', input='hello')
            result = await app.openai_responses.create(request)

        assert result is mapped
        provider.apply_sensors.assert_called_once_with(
            fn=provider.openai_responses.create,
            service_type='openai_responses',
            action='create',
            model='model-1',
        )

    async def test_create_sets_context_exception_when_provider_raises(self):
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(side_effect=RuntimeError('fail'))
        app = Llimona(providers=[provider])

        with mock.patch('llimona.interfaces.openai.mappers.IdMapper'):
            request = CreateResponse(model='prov-a/model-1', input='hello')
            with pytest.raises(RuntimeError, match='fail'):
                await app.openai_responses.create(request)


class OpenAIResponsesRetrieveTests(IsolatedAsyncioTestCase):
    async def test_retrieve_decomposes_id_and_returns_mapped_response(self):
        fake_response = mock.Mock()
        fake_response.id = 'resp-1'
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=fake_response)
        app = Llimona(providers=[provider])
        app._id_builder = _make_id_builder_mock(provider_name='prov-a', actor_id=None)

        with mock.patch('llimona.interfaces.openai.mappers.IdMapper') as MockIdMapper:  # noqa: N806
            mapped = mock.Mock()
            MockIdMapper.return_value.map_raw_response = mock.AsyncMock(return_value=mapped)

            request = RetrieveResponse(response_id='encoded-id')
            result = await app.openai_responses.retrieve(request)

        assert result is mapped
        app._id_builder.debuild_response_id.assert_awaited_once_with('encoded-id')
        provider.apply_sensors.assert_called_once_with(
            fn=provider.openai_responses.retrieve,
            service_type='openai_responses',
            action='retrieve',
        )

    async def test_retrieve_raises_when_actor_does_not_match(self):
        fake_response = mock.Mock()
        fake_response.id = 'resp-1'
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=fake_response)
        app = Llimona(providers=[provider])
        # debuild says actor_id='stored-actor', but ctx.actor is None → validate_actor(None, 'stored-actor')
        app._id_builder = _make_id_builder_mock(provider_name='prov-a', actor_id='stored-actor')

        with mock.patch('llimona.interfaces.openai.mappers.IdMapper'):
            request = RetrieveResponse(response_id='encoded-id')
            with pytest.raises(ValueError, match='Actor ID does not match'):
                await app.openai_responses.retrieve(request)


class OpenAIResponsesCancelTests(IsolatedAsyncioTestCase):
    async def test_cancel_decomposes_id_and_calls_provider(self):
        fake_response = mock.Mock()
        fake_response.id = 'resp-1'
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=fake_response)
        app = Llimona(providers=[provider])
        app._id_builder = _make_id_builder_mock(provider_name='prov-a', actor_id=None)

        with mock.patch('llimona.interfaces.openai.mappers.IdMapper') as MockIdMapper:  # noqa: N806
            mapped = mock.Mock()
            MockIdMapper.return_value.map_response = mock.AsyncMock(return_value=mapped)

            request = DeleteResponse(response_id='encoded-id')
            result = await app.openai_responses.cancel(request)

        assert result is mapped
        app._id_builder.debuild_response_id.assert_awaited_once_with('encoded-id')
        provider.apply_sensors.assert_called_once_with(
            fn=provider.openai_responses.cancel,
            service_type='openai_responses',
            action='cancel',
        )

    async def test_cancel_raises_when_actor_does_not_match(self):
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=mock.Mock())
        app = Llimona(providers=[provider])
        app._id_builder = _make_id_builder_mock(provider_name='prov-a', actor_id='stored-actor')

        with mock.patch('llimona.interfaces.openai.mappers.IdMapper'):
            request = DeleteResponse(response_id='encoded-id')
            with pytest.raises(ValueError, match='Actor ID does not match'):
                await app.openai_responses.cancel(request)


# ---------------------------------------------------------------------------
# OpenAIModels tests
# ---------------------------------------------------------------------------


class OpenAIModelsListLocalTests(IsolatedAsyncioTestCase):
    async def test_list_local_single_provider_yields_prefixed_model_ids(self):
        model_desc = _make_model_desc('gpt-4')
        provider = _make_mock_provider('prov-a', owner_id='openai', models=[model_desc])
        app = Llimona(providers=[provider])

        models = [m async for m in app.openai_models.list(provider_name='prov-a')]

        assert len(models) == 1
        assert models[0].id == 'prov-a/gpt-4'
        assert models[0].owned_by == 'openai'

    async def test_list_local_all_providers_yields_models_for_each(self):
        m1 = _make_model_desc('model-1')
        m2 = _make_model_desc('model-2')
        prov1 = _make_mock_provider('prov-a', models=[m1])
        prov2 = _make_mock_provider('prov-b', models=[m2])
        app = Llimona(providers=[prov1, prov2])

        models = [m async for m in app.openai_models.list()]
        ids = [m.id for m in models]

        assert 'prov-a/model-1' in ids
        assert 'prov-b/model-2' in ids

    async def test_list_local_single_provider_no_models_returns_empty(self):
        provider = _make_mock_provider('prov-a', models=[])
        app = Llimona(providers=[provider])

        models = [m async for m in app.openai_models.list(provider_name='prov-a')]

        assert models == []


class OpenAIModelsListRemoteTests(IsolatedAsyncioTestCase):
    async def test_list_remote_single_provider_skips_when_no_openai_models_service(self):
        svc = mock.Mock()
        svc.type = 'other_service'
        provider = _make_mock_provider('prov-a', services=[svc])
        app = Llimona(providers=[provider])

        models = [m async for m in app.openai_models.list(provider_name='prov-a', remote=True)]

        assert models == []

    async def test_list_remote_all_providers_skips_when_no_openai_models_service(self):
        svc = mock.Mock()
        svc.type = 'other_service'
        provider = _make_mock_provider('prov-a', services=[svc])
        app = Llimona(providers=[provider])

        models = [m async for m in app.openai_models.list(remote=True)]

        assert models == []

    async def test_list_remote_single_provider_yields_prefixed_model_ids(self):
        svc = mock.Mock()
        svc.type = 'openai_models'
        fake_api_model = _make_api_model('gpt-4')
        provider = _make_mock_provider('prov-a', services=[svc])

        async def _gen(ctx):
            yield fake_api_model

        provider.apply_sensors.return_value = _gen
        app = Llimona(providers=[provider])

        models = [m async for m in app.openai_models.list(provider_name='prov-a', remote=True)]

        assert len(models) == 1
        assert models[0].id == 'prov-a/gpt-4'

    async def test_list_remote_all_providers_yields_prefixed_model_ids(self):
        svc = mock.Mock()
        svc.type = 'openai_models'
        fake_api_model = _make_api_model('gpt-4')
        provider = _make_mock_provider('prov-a', services=[svc])

        async def _gen(ctx):
            yield fake_api_model

        provider.apply_sensors.return_value = _gen
        app = Llimona(providers=[provider])

        models = [m async for m in app.openai_models.list(remote=True)]

        assert len(models) == 1
        assert models[0].id == 'prov-a/gpt-4'

    async def test_list_remote_single_provider_propagates_exception(self):
        svc = mock.Mock()
        svc.type = 'openai_models'
        provider = _make_mock_provider('prov-a', services=[svc])

        async def _gen_raises(ctx):
            raise RuntimeError('provider error')
            yield  # make it an async generator

        provider.apply_sensors.return_value = _gen_raises
        app = Llimona(providers=[provider])

        with pytest.raises(RuntimeError, match='provider error'):
            async for _ in app.openai_models.list(provider_name='prov-a', remote=True):
                pass


class OpenAIModelsRetrieveTests(IsolatedAsyncioTestCase):
    async def test_retrieve_calls_provider_and_returns_model(self):
        fake_model = _make_api_model('model-1')
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=fake_model)
        app = Llimona(providers=[provider])

        result = await app.openai_models.retrieve('prov-a/model-1')

        assert result is fake_model
        provider.apply_sensors.assert_called_once_with(
            fn=provider.openai_models.retrieve,
            service_type='openai_models',
            action='retrieve',
            model='model-1',
        )


class OpenAIModelsDeleteTests(IsolatedAsyncioTestCase):
    async def test_delete_calls_provider_and_returns_result(self):
        provider = _make_mock_provider('prov-a')
        provider.apply_sensors.return_value = mock.AsyncMock(return_value=True)
        app = Llimona(providers=[provider])

        result = await app.openai_models.delete('prov-a/model-1')

        assert result is True
        provider.apply_sensors.assert_called_once_with(
            fn=provider.openai_models.delete,
            service_type='openai_models',
            action='delete',
            model='model-1',
        )
