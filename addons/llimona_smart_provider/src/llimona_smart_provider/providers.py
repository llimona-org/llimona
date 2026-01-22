from collections.abc import AsyncIterable, Sequence
from logging import Logger
from typing import Annotated, Literal, cast

from pydantic import AfterValidator, Field
from pydantic_views import AccessMode, ReadOnly

from llimona.context import Constraint, Context
from llimona.interfaces.openai import Responses as BaseResponses
from llimona.interfaces.openai.models.api_responses import CreateResponse, DeleteResponse, RetrieveResponse
from llimona.interfaces.openai.models.events import (
    ResponseStreamEvent,
)
from llimona.interfaces.openai.models.response import Response
from llimona.models.common import (
    BaseModel,
    GenericCredentials,
)
from llimona.providers import (
    BaseProvider,
    BaseProviderDesc,
    BaseProviderModel,
    BaseProviderService,
    ProviderServiceDesc,
    check_uniqueness_model_name,
)
from llimona.providers import (
    ProviderModelDesc as LlimonaProviderModelDesc,
)


class Credentials(GenericCredentials):
    pass


class ModelTarget(BaseModel):
    model: str
    constraints: list[Constraint] = Field(default_factory=list)
    system_prompts: list[str] = Field(default_factory=list)


class ProviderModelDesc(LlimonaProviderModelDesc):
    targets: list[ModelTarget] = Field(default_factory=list, min_length=1)


class ProviderDesc(BaseProviderDesc):
    type: ReadOnly[Literal['azure_openai']] = 'azure_openai'  # type: ignore

    base_url: str
    credentials: Credentials

    models: Annotated[
        Sequence[ProviderModelDesc],
        AfterValidator(check_uniqueness_model_name),
        AccessMode.READ_ONLY,
    ] = Field(default_factory=list)


class Provider(BaseProvider[ProviderDesc]):
    def __init__(self, provider: ProviderDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc=provider, logger=logger)

    def _build_service(self, service: ProviderServiceDesc) -> BaseProviderService:
        match service.type:
            case 'openai_responses':
                return Responses(provider=self, service=service, logger=self._logger.getChild('responses'))
            case _:
                raise ValueError(
                    f'Service type {service.type} no available for provider {self.provider}',
                )

    def _build_model(self, model: ProviderModelDesc) -> ProviderModel:  # type: ignore
        return ProviderModel(desc=model, provider=self, logger=self._logger.getChild(f'model.{model.name}'))


class ProviderModel(BaseProviderModel[Provider, ProviderModelDesc]):
    pass


class Responses(BaseProviderService[Provider], BaseResponses):
    async def create(
        self,
        request: Context[CreateResponse],
    ) -> Response | AsyncIterable[ResponseStreamEvent]:
        from llimona.interfaces.openai.mappers import IdMapper

        model: ProviderModel = cast(ProviderModel, self.provider.get_model(request.request.model))

        if model.desc.allowed_services and self.service.type not in model.desc.allowed_services:
            raise ValueError(
                f'Service {self.service.type} is not allowed for model'
                f' {request.request.model} of provider {self.provider}.',
            )

        for target in model.desc.targets:
            try:
                return await IdMapper(request.app).map_raw_response(
                    provider_id=self.provider.desc.name,
                    data=await request.app.openai_responses.create(
                        CreateResponse.model_validate(
                            {
                                'model': target.model,
                            },
                            by_alias=True,
                            by_name=True,
                            extra='ignore',
                        ),
                        parent_ctx=request,
                    ),
                )
            except Exception as e:
                self._logger.error(
                    f'Error creating response with model {target.model} for provider {self.provider}: {e}',
                )
                continue
        raise ValueError(
            f'All targets for model {request.request.model} of provider {self.provider} failed.',
        )

    async def retrieve(
        self,
        request: Context[RetrieveResponse],
    ) -> Response | AsyncIterable[ResponseStreamEvent]:
        from llimona.interfaces.openai.mappers import IdMapper

        self._logger.info(f'Retrieving response with ID: {request.request.response_id}')
        _, _, resp_id = await request.app.id_builder.debuild_response_id(request.request.response_id)

        self._logger.info(f'Decomposed Response ID: {resp_id}')

        return await IdMapper(request.app).map_raw_response(
            provider_id=self.provider.desc.name,
            data=await request.app.openai_responses.retrieve(
                RetrieveResponse.model_validate(
                    {
                        'response_id': resp_id,
                    }
                ),
                parent_ctx=request,
            ),
        )

    async def cancel(
        self,
        request: Context[DeleteResponse],
    ) -> Response:
        from llimona.interfaces.openai.mappers import IdMapper

        self._logger.info(f'Retrieving response with ID: {request.request.response_id}')
        _, _, resp_id = await request.app.id_builder.debuild_response_id(request.request.response_id)

        self._logger.info(f'Decomposed Response ID: {resp_id}')

        return await IdMapper(request.app).map_response(
            provider_id=self.provider.desc.name,
            data=await request.app.openai_responses.cancel(
                DeleteResponse.model_validate(
                    {
                        'response_id': resp_id,
                    }
                ),
                parent_ctx=request,
            ),
        )
