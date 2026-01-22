# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


from typing import Any, Literal

from pydantic import ConfigDict, Field

from llimona.interfaces.openai.models.content import InputItem
from llimona.interfaces.openai.models.enums import TruncationStrategy
from llimona.interfaces.openai.models.response import Reasoning
from llimona.interfaces.openai.models.tools import Tool
from llimona.models.common import BaseModel

AvailableEvents = Literal[
    'file_search_call.results', 'message.input_image.image_url', 'computer_call_output.output.image_url'
]


class CreateResponse(BaseModel):
    """Request payload for `POST /responses`."""

    model: str = Field(
        description='Model ID to generate the response (e.g., `gpt-4.1`).',
    )
    input: str | list[InputItem] = Field(
        description='Text input or list of input items (messages, references).',
    )
    include: list[AvailableEvents] | None = Field(
        default=None,
        description=(
            'Optional extra fields to include (e.g., `file_search_call.results`, `message.input_image.image_url`).'
        ),
    )
    parallel_tool_calls: bool | None = Field(
        default=True,
        description='Allow the model to run tool calls in parallel.',
    )
    store: bool | None = Field(
        default=True,
        description='Persist the response for later retrieval.',
    )
    stream: bool | None = Field(
        default=False,
        description='If true, stream events via server-sent events (SSE).',
    )
    instructions: str | None = Field(
        default=None,
        description='System/developer instructions to prepend to the context.',
    )
    max_output_tokens: int | None = Field(
        default=None,
        description='Upper bound on generated tokens (including reasoning tokens).',
    )
    reasoning: Reasoning | None = Field(
        default=None,
        description='Reasoning configuration (e.g., effort level for reasoning models).',
    )
    previous_response_id: str | None = Field(
        default=None,
        description='Link to a prior response for conversation state continuation.',
    )
    text: dict[str, Any] | None = Field(
        default=None,
        description='Text response configuration (structured outputs).',
    )
    tools: list[Tool] | None = Field(
        default=None,
        description='Tools the model may call (web search, file search, functions).',
    )
    tool_choice: str | dict[str, Any] | None = Field(
        default='auto',
        description='Tool selection strategy: `auto`, `none`, or a specific tool choice object.',
    )
    truncation: TruncationStrategy | None = Field(
        default=TruncationStrategy.DISABLED,
        description='Truncation strategy when context would overflow the model window.',
    )
    temperature: float | None = Field(
        default=1.0,
        description='Sampling temperature between 0 and 2 (higher = more random).',
    )
    top_p: float | None = Field(
        default=1.0,
        description='Nucleus sampling probability mass (0-1).',
    )
    user: str | None = Field(
        default=None,
        description='End-user identifier for abuse monitoring (optional).',
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description='Arbitrary key/value metadata to store with the response.',
    )

    model_config = ConfigDict(
        extra='allow',
        json_schema_extra={
            'examples': [
                {
                    'model': 'gpt-4.1',
                    'input': 'Tell me a three sentence bedtime story about a unicorn.',
                },
                {
                    'model': 'gpt-4.1',
                    'input': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'type': 'input_text',
                                    'text': 'what is in this image?',
                                },
                                {
                                    'type': 'input_image',
                                    'image_url': 'https://upload.wikimedia.org/.../boardwalk.jpg',
                                },
                            ],
                            'type': 'message',
                        },
                    ],
                },
                {
                    'model': 'gpt-4.1',
                    'tools': [{'type': 'web_search_preview'}],
                    'input': 'What was a positive news story from today?',
                },
                {
                    'model': 'gpt-4.1',
                    'tools': [
                        {
                            'type': 'function',
                            'name': 'get_current_weather',
                            'description': 'Get the current weather in a given location',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'location': {
                                        'type': 'string',
                                        'description': 'The city and state, e.g. San Francisco, CA',
                                    },
                                    'unit': {
                                        'type': 'string',
                                        'enum': ['celsius', 'fahrenheit'],
                                    },
                                },
                                'required': ['location', 'unit'],
                            },
                        },
                    ],
                    'input': 'What is the weather like in Boston today?',
                },
            ],
        },
    )


class RetrieveResponse(BaseModel):
    """Request paramerters for `GET /responses/{response_id}`."""

    response_id: str = Field(
        description='Unique identifier for the response.',
    )

    include: list[str] | None = Field(
        default=None,
        description=(
            'Optional extra fields to include (e.g., `file_search_call.results`, `message.input_image.image_url`).'
        ),
    )


class DeleteResponse(BaseModel):
    """Request paramerters for `DELETE /responses/{response_id}`."""

    response_id: str = Field(
        description='Unique identifier for the response.',
    )
