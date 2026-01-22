from enum import StrEnum

from pydantic import ConfigDict, Field

from llimona.models.common import BaseModel

# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class ObjectType(StrEnum):
    MODEL = 'model'
    LIST = 'list'


class BaseObject(BaseModel):
    object: ObjectType = Field(
        description='The object type (e.g., "model", "list").',
    )


class Model(BaseObject):
    """
    Describes an OpenAI model offering that can be used with the API.
    """

    id: str = Field(
        description='The model identifier, which can be referenced in the API endpoints.',
    )

    created: int = Field(
        description='The Unix timestamp (in seconds) when the model was created.',
    )

    object: ObjectType = Field(
        default=ObjectType.MODEL,
        description='The object type, which is always "model".',
    )

    owned_by: str | None = Field(
        default=None,
        description='The organization that owns the model.',
    )

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'id': 'gpt-4o',
                    'object': 'model',
                    'created': 1686935002,
                    'owned_by': 'openai',
                },
            ],
        },
    )


class ListModelsRequest(BaseModel):
    """
    Request model for listing available models.
    """

    pass


class ListModelsResponse(BaseObject):
    """
    Response from GET /v1/models.

    Lists the currently available models and provides basic information
    about each one such as the owner and availability.
    """

    object: ObjectType = Field(
        default=ObjectType.LIST,
        description='The object type, which is always "list".',
    )

    data: list[Model] = Field(
        description='List of model objects.',
    )

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'object': 'list',
                    'data': [
                        {
                            'id': 'model-id-0',
                            'object': 'model',
                            'created': 1686935002,
                            'owned_by': 'organization-owner',
                        },
                        {
                            'id': 'model-id-1',
                            'object': 'model',
                            'created': 1686935002,
                            'owned_by': 'organization-owner',
                        },
                        {
                            'id': 'model-id-2',
                            'object': 'model',
                            'created': 1686935002,
                            'owned_by': 'openai',
                        },
                    ],
                },
            ],
        },
    )


class ModelRequest(BaseModel):
    model_id: str = Field(
        description='The ID of the model ',
    )


class DeleteModelResponse(BaseObject):
    """
    Response from DELETE /v1/models/{model}.

    Indicates the deletion status of a fine-tuned model.
    You must have the Owner role in your organization to delete a model.
    """

    id: str = Field(
        description='The ID of the deleted model.',
    )

    deleted: bool = Field(
        description='Whether the model was successfully deleted.',
    )

    object: ObjectType = Field(
        default=ObjectType.MODEL,
        description='The object type (typically "model").',
    )

    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'id': 'ft:gpt-4o-mini:acemeco:suffix:abc123',
                    'object': 'model',
                    'deleted': True,
                },
            ],
        },
    )
