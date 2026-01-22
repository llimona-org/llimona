# ---------------------------------------------------------------------------
# Tool definitions for requests
# ---------------------------------------------------------------------------


from typing import Annotated, Any, Literal

from pydantic import Field

from llimona.interfaces.openai.models.enums import SearchContextSize
from llimona.models.common import BaseModel


class WebSearchTool(BaseModel):
    """Built-in web search tool configuration."""

    type: Literal['web_search_preview'] = Field(default='web_search_preview')
    domains: list[str] | None = Field(
        default=None,
        description='Optional allowed domains.',
    )
    search_context_size: SearchContextSize | None = Field(
        default=None,
        description='Result context size preference.',
    )


class FileSearchTool(BaseModel):
    """Built-in file search tool configuration."""

    type: Literal['file_search'] = Field(default='file_search')
    vector_store_ids: list[str] | None = Field(
        default=None,
        description='Vector store IDs to search.',
    )
    max_num_results: int | None = Field(
        default=None,
        description='Maximum number of results to return.',
    )


class FunctionTool(BaseModel):
    """Custom function definition exposed to the model."""

    type: Literal['function'] = Field(default='function')
    name: str = Field(description='Function name.')
    description: str | None = Field(
        default=None,
        description='Human-readable function description.',
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description='JSON Schema describing function parameters.',
    )
    strict: bool | None = Field(
        default=None,
        description='Whether to enforce parameter schema.',
    )


type Tool = Annotated[
    WebSearchTool | FileSearchTool | FunctionTool,
    Field(discriminator='type'),
]
