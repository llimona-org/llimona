from collections.abc import AsyncIterable, Callable
from logging import Logger
from typing import Any, Literal
from unittest import mock

from pydantic import ConfigDict

from llimona.context import Context
from llimona.interfaces.openai import Models as BaseModels
from llimona.interfaces.openai import Responses as BaseResponses
from llimona.interfaces.openai.models.api_models import ListModelsRequest, Model, ModelRequest
from llimona.interfaces.openai.models.api_responses import CreateResponse, DeleteResponse, RetrieveResponse
from llimona.interfaces.openai.models.events import (
    ResponseStreamEvent,
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


class Credentials(GenericCredentials):
    pass


class ProviderDesc(BaseProviderDesc):
    model_config = ConfigDict(extra='allow')

    type: Literal['mock'] = 'mock'  # type: ignore


class Provider(BaseProvider[ProviderDesc]):
    def __init__(self, provider: ProviderDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc=provider, logger=logger)

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


def make_mock(meth: Callable[..., Any]) -> Callable[..., Any]:

    return mock.Mock()


class Responses(BaseProviderService[Provider], BaseResponses):
    async def create(self, request: Context[CreateResponse]) -> Response | AsyncIterable[ResponseStreamEvent]:
        pass

    async def retrieve(self, request: Context[RetrieveResponse]) -> Response | AsyncIterable[ResponseStreamEvent]:
        pass

    async def cancel(
        self,
        request: Context[DeleteResponse],
    ) -> Response:
        pass


class Models(BaseProviderService[Provider], BaseModels):
    async def list(self, request: Context[ListModelsRequest]) -> AsyncIterable[Model]:
        pass

    async def retrieve(self, request: Context[ModelRequest]) -> Model:
        pass

    async def delete(self, request: Context[ModelRequest]) -> bool:
        pass
