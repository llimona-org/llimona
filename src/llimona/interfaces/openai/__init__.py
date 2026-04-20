from abc import ABC, abstractmethod
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING

from llimona.interfaces.openai.models.api_models import ListModelsRequest, Model, ModelRequest
from llimona.interfaces.openai.models.api_responses import CreateResponse, DeleteResponse, RetrieveResponse
from llimona.interfaces.openai.models.events import ResponseStreamEvent
from llimona.interfaces.openai.models.response import Response

if TYPE_CHECKING:
    from llimona.context import Context


class Responses(ABC):
    TYPE = 'openai_responses'

    @abstractmethod
    async def create(self, request: Context[CreateResponse]) -> Response | AsyncIterable[ResponseStreamEvent]:
        raise NotImplementedError()

    @abstractmethod
    async def retrieve(self, request: Context[RetrieveResponse]) -> Response | AsyncIterable[ResponseStreamEvent]:
        raise NotImplementedError()

    @abstractmethod
    async def cancel(self, request: Context[DeleteResponse]) -> Response:
        raise NotImplementedError()


class Models(ABC):
    TYPE = 'openai_models'

    @abstractmethod
    def list(self, request: Context[ListModelsRequest]) -> AsyncIterable[Model]:
        raise NotImplementedError()

    @abstractmethod
    async def retrieve(self, request: Context[ModelRequest]) -> Model:
        raise NotImplementedError()

    @abstractmethod
    async def delete(self, request: Context[ModelRequest]) -> bool:
        raise NotImplementedError()
