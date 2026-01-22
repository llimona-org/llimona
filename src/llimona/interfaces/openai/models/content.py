# ---------------------------------------------------------------------------
# Input content
# ---------------------------------------------------------------------------


from typing import Annotated, Any, Literal

from pydantic import Field

from llimona.interfaces.openai.models.enums import InputMessageRole, ItemStatus, OutputMessageRole
from llimona.models.common import BaseModel


class InputTextContent(BaseModel):
    """A text input to the model."""

    type: Literal['input_text'] = Field(
        default='input_text',
        description='The type of the input content. Always `input_text`.',
    )
    text: str = Field(description='User-provided text input.')


class InputImageContent(BaseModel):
    """An image input to the model."""

    type: Literal['input_image'] = Field(
        default='input_image',
        description='The type of the input content. Always `input_image`.',
    )
    image_url: str | None = Field(
        default=None,
        description='HTTPS URL for the image to load.',
    )
    image_file_id: str | None = Field(
        default=None,
        description='A file ID referencing an uploaded image.',
    )


class InputFileContent(BaseModel):
    """A file input to the model."""

    type: Literal['input_file'] = Field(
        default='input_file',
        description='The type of the input content. Always `input_file`.',
    )
    file_id: str = Field(description='The uploaded file ID.')


InputContent = Annotated[
    InputTextContent | InputImageContent | InputFileContent,
    Field(discriminator='type'),
]


class InputMessage(BaseModel):
    """A message input with a role and mixed content."""

    type: Literal['message'] = Field(
        default='message',
        description='The type of the message input.',
    )
    role: InputMessageRole = Field(description='Role of the message input.')
    content: list[InputContent] = Field(
        description='List of content parts (text, image, or file).',
    )
    status: ItemStatus | None = Field(
        default=None,
        description='Optional status when items are returned via the API.',
    )
    id: str | None = Field(
        default=None,
        description='Optional unique ID when the server returns the message.',
    )


class ItemReferenceParam(BaseModel):
    """Reference to a previously created item by ID."""

    type: Literal['item_ref'] = Field(
        default='item_ref',
        description='Always `item_ref`.',
    )
    item_id: str = Field(description='ID of the referenced item.')


InputItem = Annotated[
    InputMessage | ItemReferenceParam,
    Field(discriminator='type'),
]


# ---------------------------------------------------------------------------
# Output content and annotations
# ---------------------------------------------------------------------------


class FileCitationAnnotation(BaseModel):
    """A citation pointing to a file reference."""

    type: Literal['file_citation'] = Field(default='file_citation')
    index: int = Field(description='Character index where the citation starts.')
    file_id: str = Field(description='ID of the cited file.')
    filename: str | None = Field(
        default=None,
        description='Optional filename for display.',
    )


class UrlCitationAnnotation(BaseModel):
    """A citation pointing to a URL reference."""

    type: Literal['url_citation'] = Field(default='url_citation')
    start_index: int = Field(description='Character index where the citation starts.')
    end_index: int = Field(description='Character index where the citation ends.')
    url: str = Field(description='Referenced URL.')
    title: str | None = Field(default=None, description='Optional page title.')


Annotation = Annotated[
    FileCitationAnnotation | UrlCitationAnnotation,
    Field(discriminator='type'),
]


class OutputTextContent(BaseModel):
    """Text output from the model."""

    type: Literal['output_text'] = Field(default='output_text')
    text: str = Field(description='Generated text.')
    annotations: list[Annotation] = Field(
        default_factory=list,
        description='Optional annotations (citations, URLs).',
    )


class OutputRefusal(BaseModel):
    """A refusal from the model."""

    refusal: str
    """The refusal explanation from the model."""

    type: Literal['refusal']
    """The type of the refusal. Always `refusal`."""


class PartReasoningText(BaseModel):
    """Reasoning text from the model."""

    text: str
    """The reasoning text from the model."""

    type: Literal['reasoning_text']
    """The type of the reasoning text. Always `reasoning_text`."""


OutputContent = Annotated[
    OutputTextContent | OutputRefusal | PartReasoningText,
    Field(discriminator='type'),
]


class OutputMessage(BaseModel):
    """Assistant message produced by the model."""

    id: str = Field(description='Unique ID of the output message.')
    type: Literal['message'] = Field(default='message')
    role: OutputMessageRole = Field(default=OutputMessageRole.ASSISTANT)
    content: list[OutputContent] = Field(
        description='Content parts produced by the model.',
    )
    status: ItemStatus = Field(description='Status of the message output.')


class FileSearchToolCall(BaseModel):
    """A file search tool invocation made by the model."""

    type: Literal['file_search_call'] = Field(default='file_search_call')
    id: str = Field(description='Unique ID for the tool call.')
    status: ItemStatus = Field(description='Status of the tool call.')
    queries: list[str] | None = Field(
        default=None,
        description='Queries issued during the search.',
    )
    results: list[dict[str, Any]] | None = Field(
        default=None,
        description='Search results (when requested with include).',
    )


class WebSearchToolCall(BaseModel):
    """A web search tool invocation made by the model."""

    type: Literal['web_search_call'] = Field(default='web_search_call')
    id: str = Field(description='Unique ID for the tool call.')
    status: ItemStatus = Field(description='Status of the tool call.')


class FunctionToolCall(BaseModel):
    """A custom function call made by the model."""

    type: Literal['function_call'] = Field(default='function_call')
    id: str = Field(description='Unique ID for the tool call.')
    call_id: str = Field(description='Opaque call identifier.')
    name: str = Field(description='Function name invoked by the model.')
    arguments: str = Field(description='JSON-encoded function arguments.')
    status: ItemStatus = Field(description='Status of the function call.')


OutputItem = Annotated[
    OutputMessage | FileSearchToolCall | WebSearchToolCall | FunctionToolCall,
    Field(discriminator='type'),
]
