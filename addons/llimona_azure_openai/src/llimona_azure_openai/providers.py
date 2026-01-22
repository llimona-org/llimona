from collections.abc import AsyncIterable
from logging import Logger
from typing import Any, Literal

from openai import AsyncAzureOpenAI, AsyncStream
from openai.types.responses import (
    Response as OpenAIResponse,
)

from llimona.context import Context
from llimona.interfaces.openai import Models as BaseModels
from llimona.interfaces.openai import Responses as BaseResponses
from llimona.interfaces.openai.models.api_models import ListModelsRequest, Model, ModelRequest
from llimona.interfaces.openai.models.api_responses import CreateResponse, DeleteResponse, RetrieveResponse
from llimona.interfaces.openai.models.events import (
    ResponseStreamEvent,
    ResponseStreamEventTypeAdapter,
)
from llimona.interfaces.openai.models.response import Response
from llimona.models.common import GenericCredentials
from llimona.providers import (
    BaseProvider,
    BaseProviderDesc,
    BaseProviderModel,
    BaseProviderService,
    ProviderModelDesc,
    ProviderServiceDesc,
)
from llimona.utils import AsyncIterableMapper


class Credentials(GenericCredentials):
    pass


class ProviderDesc(BaseProviderDesc):
    type: Literal['azure_openai'] = 'azure_openai'  # type: ignore

    base_url: str
    credentials: Credentials


class Provider(BaseProvider[ProviderDesc]):
    def __init__(self, provider: ProviderDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc=provider, logger=logger)

        self.driver = AsyncAzureOpenAI(
            base_url=self.provider.base_url,
            api_key=self.provider.credentials.api_key.get_secret_value(),
            api_version='v1',
            max_retries=0,
        )

    def _build_service(self, service: ProviderServiceDesc) -> BaseProviderService:
        match service.type:
            case 'openai_responses':
                return Responses(provider=self, service=service, logger=self._logger.getChild('responses'))
            case 'openai_models':
                return Models(provider=self, service=service, logger=self._logger.getChild('models'))
            case _:
                raise ValueError(
                    f'Service type {service.type} no available for provider {self.provider}',
                )

    def _build_model(self, model: ProviderModelDesc) -> BaseProviderModel:
        return ProviderModel(desc=model, provider=self, logger=self._logger.getChild(f'model.{model.name}'))


class ProviderModel(BaseProviderModel[Provider, ProviderModelDesc]):
    pass


class Responses(BaseProviderService[Provider], BaseResponses):
    def _map_raw_response(
        self,
        raw_response: OpenAIResponse | AsyncStream[ResponseStreamEvent],
    ) -> Response | AsyncIterable[ResponseStreamEvent]:
        if isinstance(raw_response, AsyncStream):
            return self._map_stream(raw_response)

        return self._map_response(raw_response)

    def _map_stream(
        self,
        raw_stream: AsyncStream[ResponseStreamEvent],
    ) -> AsyncIterable[ResponseStreamEvent]:
        return AsyncIterableMapper(raw_stream, self._map_stream_event)

    def _map_stream_event(
        self,
        raw_event: ResponseStreamEvent,
    ) -> ResponseStreamEvent:
        new_data = {}
        if 'response' in raw_event.model_fields_set:
            new_data['response'] = self._map_raw_response(raw_event.response)  # type: ignore
        return ResponseStreamEventTypeAdapter.validate_python(
            raw_event.model_dump() | new_data,
        )

    def _map_response(self, raw_response: OpenAIResponse) -> Response:
        return Response.model_validate(
            raw_response.model_dump(),
            by_alias=True,
            by_name=True,
            extra='ignore',
        )

    async def create(self, request: Context[CreateResponse]) -> Response | AsyncIterable[ResponseStreamEvent]:
        model = self.provider.get_model(request.request.model)

        if model.desc.allowed_services and self.service.type not in model.desc.allowed_services:
            raise ValueError(
                f'Model {request.request.model} is not allowed for the provider {self.provider.desc.name}.',
            )

        params: dict[str, Any] = {'model': request.request.model}

        if 'input' in request.request.model_fields_set:
            input_value = request.request.input
            params['input'] = input_value if isinstance(input_value, str) else [i.model_dump() for i in input_value]

        params.update(
            request.request.model_dump(
                include={
                    'include',
                    'instructions',
                    'max_output_tokens',
                    'parallel_tool_calls',
                    'store',
                    'stream',
                    'reasoning',
                    'previous_response_id',
                    'text',
                    'truncation',
                    'tools',
                    'tool_choice',
                    'temperature',
                    'top_p',
                    'user',
                    'metadata',
                },
                exclude_unset=True,
                by_alias=True,
                exclude_defaults=True,
            )
        )

        try:
            return self._map_raw_response(await self.provider.driver.responses.create(**params))
        except Exception as e:
            breakpoint()
            self._logger.error(f'Error creating response: {e}')
            raise

    async def retrieve(self, request: Context[RetrieveResponse]) -> Response | AsyncIterable[ResponseStreamEvent]:
        return self._map_raw_response(
            await self.provider.driver.responses.retrieve(
                response_id=request.request.response_id,
                **{
                    k: v
                    for k, v in request.request.model_dump(include={'include'}, by_alias=True).items()
                    if v is not None
                },
            )
        )

    async def cancel(
        self,
        request: Context[DeleteResponse],
    ) -> Response:
        return self._map_response(
            await self.provider.driver.responses.cancel(
                response_id=request.request.response_id,
            )
        )


class Models(BaseProviderService[Provider], BaseModels):
    async def list(self, request: Context[ListModelsRequest]) -> AsyncIterable[Model]:
        self._logger.info('Listing models...')

        async for model in self.provider.driver.models.list():
            yield Model.model_validate(
                {'id': model.id, 'owned_by': model.owned_by, 'created': model.created},
                by_alias=True,
                by_name=True,
                extra='ignore',
            )

    async def retrieve(self, request: Context[ModelRequest]) -> Model:
        return Model.model_validate(
            await self.provider.driver.models.retrieve(model=request.request.model_id),
            by_alias=True,
            by_name=True,
            extra='ignore',
        )

    async def delete(self, request: Context[ModelRequest]) -> bool:
        result = await self.provider.driver.models.delete(model=request.request.model_id)
        return result.deleted
