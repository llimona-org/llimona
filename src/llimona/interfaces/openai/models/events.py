from typing import Annotated, Literal

from pydantic import ConfigDict, Field, TypeAdapter

from llimona.interfaces.openai.models.content import OutputContent
from llimona.interfaces.openai.models.response import Response, ResponseOutputItem
from llimona.models.common import BaseModel


class BaseResponseStreamEvent(BaseModel):
    """Streaming event union for SSE responses.

    We keep this permissive (`extra="allow"`) while discriminating on `type`
    so callers can pattern-match on event names like `response.created`,
    `response.in_progress`, `response.output_text.delta`, etc.
    """

    model_config = ConfigDict(extra='allow')

    type: str = Field(description='Event discriminator (e.g., `response.created`).')


class ResponseCreatedEvent(BaseResponseStreamEvent):
    """An event that is emitted when a response is created."""

    response: Response
    """The response that was created."""

    sequence_number: int
    """The sequence number for this event."""

    type: Literal['response.created']  # type: ignore
    """The type of the event. Always `response.created`."""


class ResponseInProgressEvent(BaseResponseStreamEvent):
    """Emitted when the response is in progress."""

    response: Response
    """The response that is in progress."""

    sequence_number: int
    """The sequence number of this event."""

    type: Literal['response.in_progress']  # type: ignore
    """The type of the event. Always `response.in_progress`."""


class ResponseOutputItemAddedEvent(BaseResponseStreamEvent):
    """Emitted when a new output item is added."""

    item: ResponseOutputItem
    """The output item that was added."""

    output_index: int
    """The index of the output item that was added."""

    sequence_number: int
    """The sequence number of this event."""

    type: Literal['response.output_item.added']  # type: ignore
    """The type of the event. Always `response.output_item.added`."""


class ResponseContentPartAddedEvent(BaseResponseStreamEvent):
    """Emitted when a new content part is added."""

    content_index: int
    """The index of the content part that was added."""

    item_id: str
    """The ID of the output item that the content part was added to."""

    output_index: int
    """The index of the output item that the content part was added to."""

    part: OutputContent
    """The content part that was added."""

    sequence_number: int
    """The sequence number of this event."""

    type: Literal['response.content_part.added']  # type: ignore
    """The type of the event. Always `response.content_part.added`."""


class ResponseTextDeltaEvent(BaseResponseStreamEvent):
    """Emitted when there is an additional text delta."""

    content_index: int
    """The index of the content part that the text delta was added to."""

    delta: str
    """The text delta that was added."""

    item_id: str
    """The ID of the output item that the text delta was added to."""

    output_index: int
    """The index of the output item that the text delta was added to."""

    sequence_number: int
    """The sequence number for this event."""

    type: Literal['response.output_text.delta']  # type: ignore
    """The type of the event. Always `response.output_text.delta`."""


class ResponseTextDoneEvent(BaseResponseStreamEvent):
    """Emitted when text content is finalized."""

    content_index: int
    """The index of the content part that the text content is finalized."""

    item_id: str
    """The ID of the output item that the text content is finalized."""

    output_index: int
    """The index of the output item that the text content is finalized."""

    sequence_number: int
    """The sequence number for this event."""

    text: str
    """The text content that is finalized."""

    type: Literal['response.output_text.done']  # type: ignore
    """The type of the event. Always `response.output_text.done`."""


class ResponseContentPartDoneEvent(BaseResponseStreamEvent):
    """Emitted when a content part is done."""

    content_index: int
    """The index of the content part that is done."""

    item_id: str
    """The ID of the output item that the content part was added to."""

    output_index: int
    """The index of the output item that the content part was added to."""

    part: OutputContent
    """The content part that is done."""

    sequence_number: int
    """The sequence number of this event."""

    type: Literal['response.content_part.done']  # type: ignore
    """The type of the event. Always `response.content_part.done`."""


class ResponseOutputItemDoneEvent(BaseResponseStreamEvent):
    """Emitted when an output item is marked done."""

    item: ResponseOutputItem
    """The output item that was marked done."""

    output_index: int
    """The index of the output item that was marked done."""

    sequence_number: int
    """The sequence number of this event."""

    type: Literal['response.output_item.done']  # type: ignore
    """The type of the event. Always `response.output_item.done`."""


class ResponseCompletedEvent(BaseResponseStreamEvent):
    """Emitted when the model response is complete."""

    response: Response
    """Properties of the completed response."""

    sequence_number: int
    """The sequence number for this event."""

    type: Literal['response.completed']  # type: ignore
    """The type of the event. Always `response.completed`."""


type ResponseStreamEvent = Annotated[
    ResponseCreatedEvent
    | ResponseInProgressEvent
    | ResponseOutputItemAddedEvent
    | ResponseContentPartAddedEvent
    | ResponseTextDeltaEvent
    | ResponseTextDoneEvent
    | ResponseContentPartDoneEvent
    | ResponseOutputItemDoneEvent
    | ResponseCompletedEvent,
    Field(discriminator='type'),
]

ResponseStreamEventTypeAdapter: TypeAdapter[ResponseStreamEvent] = TypeAdapter(ResponseStreamEvent)
