from abc import ABC
from collections.abc import AsyncIterable, Awaitable, Callable, Iterable, Sequence
from functools import lru_cache, reduce
from logging import Logger, getLogger
from typing import TYPE_CHECKING, overload
from weakref import ref

from llimona.interfaces.openai.models.api_models import ListModelsRequest, Model, ModelRequest
from llimona.interfaces.openai.models.api_responses import CreateResponse, DeleteResponse, RetrieveResponse
from llimona.interfaces.openai.models.events import ResponseStreamEvent
from llimona.interfaces.openai.models.response import Response
from llimona.utils import LoggerMixin

if TYPE_CHECKING:
    from llimona.context import ActionContext, Actor, Constraint, Context, Origin
    from llimona.id_builders import BaseIdBuilder
    from llimona.providers import BaseProvider
    from llimona.sensors import BaseSensor


class Llimona:
    def __init__(self, providers: Iterable[BaseProvider], id_builder: BaseIdBuilder | None = None) -> None:
        from llimona.id_builders import PlainIdBuilder, PlainIdBuilderDesc

        self._providers: dict[str, BaseProvider] = {provider.provider.name: provider for provider in providers}
        self._id_builder = id_builder or PlainIdBuilder(desc=PlainIdBuilderDesc())

        self.openai_responses = OpenAIResponses(app=self)
        self.openai_models = OpenAIModels(app=self)

    @property
    def id_builder(self) -> BaseIdBuilder:
        return self._id_builder

    def decompose_model(self, model: str) -> tuple[str, str]:
        return tuple(model.split('/', 1))  # type: ignore

    def get_provider(self, provider: str) -> BaseProvider:
        return self._providers[provider]

    def register_provider(self, provider: BaseProvider) -> None:
        assert provider.provider.name not in self._providers, (
            f"Provider with name '{provider.provider.name}' is already registered"
        )

        self._providers[provider.provider.name] = provider

    async def validate_actor(self, request_actor_id: str | None, resource_create_actor_id: str | None) -> None:
        if request_actor_id != resource_create_actor_id:
            raise ValueError('Actor ID does not match the expected actor ID.')

    def build_context[TRequest](
        self,
        request: TRequest,
        *,
        action: ActionContext | None = None,
        origin: Origin | None = None,
        actor: Actor | None = None,
        constraints: list[Constraint] | None = None,
        parent: Context | None = None,
    ) -> Context[TRequest]:
        from llimona.context import Context

        return Context(
            app=self,
            action=action,
            request=request,
            origin=origin,
            actor=actor,
            constraints=constraints,
            parent=parent,
        )


class BaseService(LoggerMixin, ABC):
    TYPE: str

    def __init__(
        self,
        app: Llimona,
        *,
        logger: Logger | None = None,
    ) -> None:
        super().__init__(
            logger=logger
            or getLogger(
                f'aicc_proxy.{self.TYPE}',
            ),
        )

        self._app = ref(app)

    def _build_context[T](
        self,
        request: T,
        provider: str,
        service_action: str,
        model: str | None = None,
        parent_ctx: Context | None = None,
        constraints: Sequence[Constraint] | None = None,
    ) -> Context[T]:
        from llimona.context import ActionContext, Context

        if parent_ctx is not None:
            if parent_ctx.app != self.app:
                raise ValueError('Parent context belongs to a different app instance')
            return parent_ctx.create_subcontext(
                ActionContext(provider=provider, service=self.TYPE, service_action=service_action, model=model),
                request,
                constraints=constraints,
            )
        else:
            return Context(
                app=self.app,
                action=ActionContext(provider=provider, service=self.TYPE, service_action=service_action, model=model),
                request=request,
                origin=None,
                actor=None,
                constraints=constraints,
            )

    @property
    def app(self) -> Llimona:
        app = self._app()
        if app is None:
            raise ReferenceError('The app reference is no longer valid')
        return app

    @overload
    def apply_sensors[**Params, O](
        self, fn: Callable[Params, Awaitable[O]], action: str, model: str | None = None
    ) -> Callable[Params, Awaitable[O]]: ...

    @overload
    def apply_sensors[**Params, O](
        self, fn: Callable[Params, AsyncIterable[O]], action: str, model: str | None = None
    ) -> Callable[Params, AsyncIterable[O]]: ...

    @lru_cache(maxsize=128)  # noqa: B019
    def apply_sensors[**Params, O](
        self,
        sensors: Iterable[BaseSensor],
        fn: Callable[Params, Awaitable[O] | AsyncIterable[O]],
        action: str,
        model: str | None = None,
    ) -> Callable[Params, Awaitable[O] | AsyncIterable[O]]:
        return reduce(lambda f, sensor: sensor(f), sensors, fn)  # type: ignore


class OpenAIResponses(BaseService):
    TYPE = 'openai_responses'

    async def create(
        self, request: CreateResponse, *, parent_ctx: Context | None = None, constraints: list[Constraint] | None = None
    ) -> Response | AsyncIterable[ResponseStreamEvent]:
        from llimona.interfaces.openai.mappers import IdMapper

        self._logger.info(f'Creating response for model: {request.model}')

        provider_name, provider_model_name = self.app.decompose_model(request.model)

        with self._build_context(
            request=request.model_copy(update={'model': provider_model_name}),
            provider=provider_name,
            service_action='create',
            model=provider_model_name,
            parent_ctx=parent_ctx,
            constraints=constraints,
        ) as ctx:
            provider = self.app.get_provider(provider_name)
            data = await provider.apply_sensors(
                fn=provider.openai_responses.create,
                service_type=self.TYPE,
                action='create',
                model=provider_model_name,
            )(ctx)

            return await IdMapper(self.app).map_raw_response(provider_name, data, ctx.actor.id if ctx.actor else None)

    async def retrieve(
        self,
        request: RetrieveResponse,
        *,
        parent_ctx: Context | None = None,
        constraints: Sequence[Constraint] | None = None,
    ) -> Response | AsyncIterable[ResponseStreamEvent]:
        from llimona.interfaces.openai.mappers import IdMapper

        self._logger.info(f'Retrieving response with ID: {request.response_id}')
        provider_name, actor_id, resp_id = await self.app.id_builder.debuild_response_id(request.response_id)

        self._logger.info(
            f'Decomposed ID - Response ID: {resp_id}, Provider Name: {provider_name}, Actor ID: {actor_id}'
        )

        with self._build_context(
            request=request.model_copy(update={'response_id': resp_id}),
            provider=provider_name,
            service_action='create',
            model=None,
            parent_ctx=parent_ctx,
            constraints=constraints,
        ) as ctx:
            await self.app.validate_actor(ctx.actor.id if ctx.actor else None, actor_id)

            provider = self.app.get_provider(provider_name)
            data = await provider.apply_sensors(
                fn=provider.openai_responses.retrieve,
                service_type=self.TYPE,
                action='retrieve',
            )(ctx)
            return await IdMapper(self.app).map_raw_response(provider_name, data, ctx.actor.id if ctx.actor else None)

    async def cancel(
        self,
        request: DeleteResponse,
        *,
        parent_ctx: Context | None = None,
        constraints: Sequence[Constraint] | None = None,
    ) -> Response:
        from llimona.interfaces.openai.mappers import IdMapper

        self._logger.info(f'Cancelling response with ID: {request.response_id}')

        provider_name, actor_id, resp_id = await self.app.id_builder.debuild_response_id(request.response_id)

        self._logger.info(
            f'Decomposed ID - Response ID: {resp_id}, Provider Name: {provider_name}, Actor ID: {actor_id}'
        )

        with self._build_context(
            request=request.model_copy(update={'response_id': resp_id}),
            provider=provider_name,
            service_action='cancel',
            model=None,
            parent_ctx=parent_ctx,
            constraints=constraints,
        ) as ctx:
            await self.app.validate_actor(ctx.actor.id if ctx.actor else None, actor_id)

            provider = self.app.get_provider(provider_name)
            data = await provider.apply_sensors(
                fn=provider.openai_responses.cancel,
                service_type=self.TYPE,
                action='cancel',
            )(ctx)
            return await IdMapper(self.app).map_response(provider_name, data, ctx.actor.id if ctx.actor else None)


class OpenAIModels(BaseService):
    TYPE = 'openai_models'

    def _list_local_models(self, provider: BaseProvider) -> Iterable[Model]:
        for model in provider.provider.models:
            yield Model.model_validate(
                {
                    'id': '/'.join([provider.provider.name, model.name]),
                    'owned_by': provider.provider.owner_id,
                    'created': int(model.created.timestamp()),
                },
            )

    async def list(
        self,
        *,
        provider_name: str | None = None,
        remote: bool = False,
        parent_ctx: Context | None = None,
        constraints: Sequence[Constraint] | None = None,
    ) -> AsyncIterable[Model]:
        self._logger.info('Listing models...')

        if provider_name is not None:
            self._logger.info(f'Listing models from provider: {provider_name}')
            prov = self.app.get_provider(provider_name)

            if not remote:
                self._logger.info(f'Listing local models from provider: {provider_name}')

                for model in self._list_local_models(prov):
                    yield model
                return

            if not any(s.type == 'openai_models' for s in prov.provider.services):
                self._logger.info(f'Provider {provider_name} does not support openai_models service. Skipping...')
                return

            ctx = self._build_context(
                request=ListModelsRequest(),
                provider=provider_name,
                service_action='list',
                model=None,
                parent_ctx=parent_ctx,
                constraints=constraints,
            )
            try:
                provider = self.app.get_provider(provider_name)
                async for model in provider.apply_sensors(
                    fn=prov.openai_models.list,
                    service_type=self.TYPE,
                    action='list',
                    model=None,
                )(ctx):
                    yield model.model_copy(update={'id': '/'.join([provider_name, model.id])})

                return
            except Exception as e:
                ctx.set_exception(e)
                raise

        for prov_id, prov in self.app._providers.items():
            self._logger.info(f'Listing models from provider: {prov_id}')
            if not remote:
                self._logger.info(f'Listing local models from provider: {prov_id}')

                for model in self._list_local_models(prov):
                    yield model
                continue

            if not any(s.type == 'openai_models' for s in prov.provider.services):
                self._logger.info(f'Provider {prov_id} does not support openai_models service. Skipping...')
                continue

            with self._build_context(
                request=ListModelsRequest(),
                provider=prov_id,
                service_action='list',
                model=None,
                constraints=constraints,
            ) as ctx:
                async for model in prov.apply_sensors(
                    fn=prov.openai_models.list,
                    service_type=self.TYPE,
                    action='list',
                    model=None,
                )(ctx):
                    yield model.model_copy(update={'id': '/'.join([prov_id, model.id])})

    async def retrieve(
        self, model_name: str, *, parent_ctx: Context | None = None, constraints: Sequence[Constraint] | None = None
    ) -> Model:
        self._logger.info(f'Retrieving model with ID: {model_name}')
        provider_name, provider_model_name = model_name.split('/', 1)

        self._logger.info(f'Parsed model name - Provider name: {provider_name}, Model name: {provider_model_name}')

        with self._build_context(
            request=ModelRequest(model_id=provider_model_name),
            provider=provider_name,
            service_action='retrieve',
            model=provider_model_name,
            constraints=constraints,
            parent_ctx=parent_ctx,
        ) as ctx:
            provider = self.app.get_provider(provider_name)
            return await provider.apply_sensors(
                fn=provider.openai_models.retrieve,
                service_type=self.TYPE,
                action='retrieve',
                model=provider_model_name,
            )(ctx)

    async def delete(
        self, model_name: str, *, parent_ctx: Context | None = None, constraints: Sequence[Constraint] | None = None
    ) -> bool:
        self._logger.info(f'Deleting model with ID: {model_name}')

        provider_name, provider_model_name = model_name.split('/', 1)

        self._logger.info(f'Parsed model name - Provider name: {provider_name}, Model name: {provider_model_name}')

        with self._build_context(
            request=ModelRequest(model_id=provider_model_name),
            provider=provider_name,
            service_action='delete',
            model=provider_model_name,
            parent_ctx=parent_ctx,
            constraints=constraints,
        ) as ctx:
            provider = self.app.get_provider(provider_name)
            return await provider.apply_sensors(
                fn=provider.openai_models.delete,
                service_type=self.TYPE,
                action='delete',
                model=provider_model_name,
            )(ctx)
