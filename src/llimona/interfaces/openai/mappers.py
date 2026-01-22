from collections.abc import AsyncIterable
from functools import partial
from typing import TYPE_CHECKING

from llimona.interfaces.openai.models.events import ResponseStreamEvent
from llimona.interfaces.openai.models.response import Response
from llimona.utils import AsyncIterableMapper

if TYPE_CHECKING:
    from llimona.app import Llimona


class IdMapper:
    def __init__(self, app: Llimona):
        self.app = app

    async def map_raw_response(
        self, provider_id: str, data: Response | AsyncIterable[ResponseStreamEvent], actor_id: str | None = None
    ):
        if isinstance(data, Response):
            return await self.map_response(provider_id, data, actor_id)
        return await self.map_stream_response(provider_id, data, actor_id)

    async def map_stream_response(
        self, provider_id: str, data: AsyncIterable[ResponseStreamEvent], actor_id: str | None = None
    ):
        if isinstance(data, AsyncIterableMapper):
            data.add_mapper(partial(self.map_event, provider_id=provider_id, actor_id=actor_id))
            return data

        async def stream_mapper():
            async for event in data:
                yield await self.map_event(event, provider_id=provider_id, actor_id=actor_id)

        return stream_mapper()

    async def map_response(self, provider_id: str, data: Response, actor_id: str | None = None):
        return self.remap_response_id(
            data,
            await self.app.id_builder.build_response_id(
                provider_id=provider_id, actor_id=actor_id or '', response_id=data.id
            ),
        )

    async def map_event[T: ResponseStreamEvent](self, event: T, provider_id: str, actor_id: str | None = None) -> T:
        if 'response' in event.model_fields_set:
            return event.model_copy(
                update={
                    'response': self.remap_response_id(
                        event.response,  # type: ignore
                        await self.app.id_builder.build_response_id(
                            provider_id=provider_id,
                            actor_id=actor_id or '',
                            response_id=event.response.id,  # type: ignore
                        ),
                    )
                }
            )
        return event

    def remap_response_id(self, response: Response, new_id: str) -> Response:
        return response.model_copy(update={'id': new_id})
