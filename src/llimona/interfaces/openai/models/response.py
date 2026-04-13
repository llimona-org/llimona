from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field

from llimona.interfaces.openai.models.content import (
    FileSearchToolCall,
    FunctionToolCall,
    InputMessage,
    OutputItem,
    OutputMessage,
    WebSearchToolCall,
)
from llimona.interfaces.openai.models.enums import (
    ReasoningEffort,
    ResponseErrorCode,
    ResponseStatus,
    TruncationStrategy,
)
from llimona.interfaces.openai.models.tools import Tool
from llimona.models.common import BaseModel

# ---------------------------------------------------------------------------
# Response object and helpers
# ---------------------------------------------------------------------------


class Reasoning(BaseModel):
    effort: ReasoningEffort | None = Field(
        default=None,
        description='Model effort level (e.g., `high` for reasoning models).',
    )
    summary: str | None = Field(
        default=None,
        description='Optional reasoning summary text.',
    )


class ResponseUsage(BaseModel):
    """Token usage details for a response."""

    input_tokens: int = Field(description='Number of input tokens.')
    input_tokens_details: dict[str, Any] = Field(
        description='Breakdown of input tokens (e.g., cached_tokens).',
    )
    output_tokens: int = Field(description='Number of output tokens.')
    output_tokens_details: dict[str, Any] = Field(
        description='Breakdown of output tokens (e.g., reasoning_tokens).',
    )
    total_tokens: int = Field(description='Total tokens used.')


class ResponseError(BaseModel):
    """Error object returned when the model fails to generate a response."""

    code: ResponseErrorCode | None = Field(
        default=None,
        description='Error code (`server_error`, `rate_limit_exceeded`, ...).',
    )
    message: str = Field(description='Human-readable error message.')


class Response(BaseModel):
    """The Response object returned by the Responses API."""

    id: str = Field(description='Unique identifier for this response.')
    object: Literal['response'] = Field(default='response')
    status: ResponseStatus = Field(description='Current generation status.')
    created_at: int = Field(description='Unix timestamp when created (seconds).')
    error: ResponseError | None = Field(
        default=None,
        description='Error details when status is `failed`.',
    )
    incomplete_details: dict[str, Any] | None = Field(
        default=None,
        description='Why a response is incomplete (if applicable).',
    )
    instructions: str | None = Field(
        default=None,
        description='Optional system/developer instructions.',
    )
    max_output_tokens: int | None = Field(
        default=None,
        description='Upper bound for generated tokens (including reasoning tokens).',
    )
    model: str = Field(
        description='Model ID used to generate the response (e.g., `gpt-4.1`).',
    )
    output: list[OutputItem] = Field(
        description='Ordered list of content/tool call outputs.',
    )
    output_text: str | None = Field(
        default=None,
        description='SDK convenience aggregation of all output_text parts.',
    )
    reasoning: Reasoning | None = Field(
        default=None,
        description='Reasoning metadata (effort, summary).',
    )
    store: bool | None = Field(
        default=None,
        description='Whether the response is stored server-side.',
    )
    temperature: float | None = Field(
        default=None,
        description='Sampling temperature between 0 and 2 (higher = more random).',
    )
    text: dict[str, Any] | None = Field(
        default=None,
        description='Text response configuration (e.g., structured outputs).',
    )
    tool_choice: str | dict[str, Any] | None = Field(
        default=None,
        description='How the model should pick tools (auto/none/specific).',
    )
    tools: list[Tool] = Field(
        default_factory=list,
        description='Tools the model may call.',
    )
    top_p: float | None = Field(
        default=None,
        description='Nucleus sampling parameter between 0 and 1.',
    )
    truncation: TruncationStrategy | None = Field(
        default=TruncationStrategy.DISABLED,
        description='Truncation strategy when context would exceed the window.',
    )
    usage: ResponseUsage | None = Field(
        default=None,
        description='Token usage accounting.',
    )
    user: str | None = Field(
        default=None,
        description='End-user identifier for abuse monitoring (optional).',
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description='Arbitrary key/value metadata.',
    )
    previous_response_id: str | None = Field(
        default=None,
        description='ID of the previous response when continuing a conversation.',
    )
    parallel_tool_calls: bool | None = Field(
        default=True,
        description='Whether the model may run tool calls in parallel.',
    )

    model_config = ConfigDict(
        extra='allow',
        json_schema_extra={
            'examples': [
                {
                    'id': 'resp_67ccd3a9da748190baa7f1570fe91ac604becb25c45c1d41',
                    'object': 'response',
                    'created_at': 1741476777,
                    'status': 'completed',
                    'error': None,
                    'incomplete_details': None,
                    'instructions': None,
                    'max_output_tokens': None,
                    'model': 'gpt-4o-2024-08-06',
                    'output': [
                        {
                            'type': 'message',
                            'id': 'msg_67ccd3acc8d48190a77525dc6de64b4104becb25c45c1d41',
                            'status': 'completed',
                            'role': 'assistant',
                            'content': [
                                {
                                    'type': 'output_text',
                                    'text': 'The image depicts a scenic landscape with a wooden '
                                    'boardwalk or pathway leading through lush, green grass under '
                                    'a blue sky with some clouds.',
                                    'annotations': [],
                                },
                            ],
                        },
                    ],
                    'parallel_tool_calls': True,
                    'previous_response_id': None,
                    'reasoning': {'effort': None, 'summary': None},
                    'store': True,
                    'temperature': 1.0,
                    'text': {'format': {'type': 'text'}},
                    'tool_choice': 'auto',
                    'tools': [],
                    'top_p': 1.0,
                    'truncation': 'disabled',
                    'usage': {
                        'input_tokens': 328,
                        'input_tokens_details': {'cached_tokens': 0},
                        'output_tokens': 52,
                        'output_tokens_details': {'reasoning_tokens': 0},
                        'total_tokens': 380,
                    },
                    'user': None,
                    'metadata': {},
                },
            ],
        },
    )


class ResponseItemList(BaseModel):
    """Paginated list of input items for a response."""

    object: Literal['list'] = Field(default='list')
    data: list[InputMessage | OutputMessage | FileSearchToolCall | FunctionToolCall | WebSearchToolCall] = Field(
        description='Items that contributed to the response.',
    )
    has_more: bool = Field(description='Whether more items are available.')
    first_id: str = Field(description='ID of the first item in this page.')
    last_id: str = Field(description='ID of the last item in this page.')

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'object': 'list',
                    'data': [
                        {
                            'id': 'msg_abc123',
                            'type': 'message',
                            'role': 'user',
                            'content': [
                                {
                                    'type': 'input_text',
                                    'text': 'Tell me a three sentence bedtime story about a unicorn.',
                                },
                            ],
                        },
                    ],
                    'first_id': 'msg_abc123',
                    'last_id': 'msg_abc123',
                    'has_more': False,
                },
            ],
        },
    )


type ResponseOutputItem = Annotated[
    OutputMessage,
    Field(discriminator='type'),
]
