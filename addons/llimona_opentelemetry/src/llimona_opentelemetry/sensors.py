import inspect
from abc import ABC
from collections.abc import AsyncIterable, Awaitable
from functools import wraps
from itertools import chain
from typing import Literal, cast, overload

from opentelemetry import trace
from opentelemetry.semconv._incubating.attributes import gen_ai_attributes

from llimona.context import Action, ActionIterable, ActionSingle, Context
from llimona.interfaces.openai.models.api_responses import CreateResponse
from llimona.interfaces.openai.models.content import InputImageContent, InputMessage, InputTextContent
from llimona.sensors import BaseSensor, BaseSensorDesc


def apply_attributes_to_create_request(span: trace.Span, request: Context[CreateResponse]) -> None:
    if request.action:
        span.set_attribute(gen_ai_attributes.GEN_AI_PROVIDER_NAME, request.action.provider)
        span.set_attribute(
            gen_ai_attributes.GEN_AI_OPERATION_NAME, '.'.join([request.action.service, request.action.service_action])
        )
    span.set_attribute(
        gen_ai_attributes.GEN_AI_REQUEST_MODEL,
        request.action.model if request.action and request.action.model else request.request.model,
    )


class OpentelemetrySensorDesc(BaseSensorDesc):
    type: Literal['opentelemetry'] = 'opentelemetry'  # type: ignore


class OpentelemetrySensor[TModelDesc: OpentelemetrySensorDesc](BaseSensor[TModelDesc], ABC):
    @overload
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: ActionSingle[TRequest, TResponse, TArgs, TKwargs]
    ) -> ActionSingle[TRequest, TResponse, TArgs, TKwargs]: ...

    @overload
    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: ActionIterable[TRequest, TResponse, TArgs, TKwargs]
    ) -> ActionIterable[TRequest, TResponse, TArgs, TKwargs]: ...

    def __call__[TRequest, TResponse, TArgs, TKwargs](
        self, fn: Action[TRequest, TResponse, TArgs, TKwargs]
    ) -> Action[TRequest, TResponse, TArgs, TKwargs]:
        if not inspect.isasyncgen(fn):

            @wraps(fn)
            async def wrapper(request: Context[TRequest], *args: TArgs, **kwargs: TKwargs) -> TResponse:  # pyright: ignore[reportRedeclaration]
                try:
                    _, tracer = request.get_metadata(trace.Tracer)  # type: ignore
                except ValueError:
                    tracer = trace.get_tracer_provider().get_tracer(__name__)

                with tracer.start_as_current_span(self._build_span_name(request), kind=trace.SpanKind.INTERNAL) as span:
                    self.apply_request_attributes(span, cast(Context[CreateResponse], request))

                    return await cast(Awaitable[TResponse], fn(request, *args, **kwargs))
        else:

            @wraps(fn)
            async def wrapper(request: Context[TRequest], *args: TArgs, **kwargs: TKwargs) -> AsyncIterable[TResponse]:
                try:
                    _, tracer = request.get_metadata(trace.Tracer)  # type: ignore
                except ValueError:
                    tracer = trace.get_tracer_provider().get_tracer(__name__)

                with tracer.start_as_current_span(self._build_span_name(request), kind=trace.SpanKind.INTERNAL) as span:
                    self.apply_request_attributes(span, cast(Context[CreateResponse], request))

                    async for item in cast(AsyncIterable[TResponse], fn(request, *args, **kwargs)):
                        yield item

        return cast(Action[TRequest, TResponse, TArgs, TKwargs], wrapper)

    def _build_span_name(self, request: Context) -> str:
        if request.action:
            return '.'.join([request.action.service, request.action.service_action])
        return f'sensor.{self.desc.name}'

    def apply_request_attributes(self, span: trace.Span, request: Context) -> None:
        if request.action:
            span.set_attribute(gen_ai_attributes.GEN_AI_PROVIDER_NAME, request.action.provider)
            span.set_attribute(
                gen_ai_attributes.GEN_AI_OPERATION_NAME,
                '.'.join([request.action.service, request.action.service_action]),
            )

        if request.action and request.action.model:
            span.set_attribute(gen_ai_attributes.GEN_AI_REQUEST_MODEL, request.action.model)
        elif isinstance(request.request, CreateResponse):
            span.set_attribute(gen_ai_attributes.GEN_AI_REQUEST_MODEL, request.request.model)

        if request.conversation:
            span.set_attribute(gen_ai_attributes.GEN_AI_CONVERSATION_ID, request.conversation.id)

        if request.actor:
            span.set_attribute(gen_ai_attributes.GEN_AI_AGENT_NAME, request.actor.id)

        if isinstance(request.request, CreateResponse):
            if request.request.temperature is not None:
                span.set_attribute(gen_ai_attributes.GEN_AI_REQUEST_TEMPERATURE, request.request.temperature)

            if request.request.top_p is not None:
                span.set_attribute(gen_ai_attributes.GEN_AI_REQUEST_TOP_P, request.request.top_p)

            if request.request.input is not None:
                text = list(
                    filter(
                        None,
                        chain.from_iterable(
                            [
                                [
                                    c.text
                                    if isinstance(c, InputTextContent)
                                    else c.image_url
                                    if isinstance(c, InputImageContent)
                                    else c.file_id
                                    for c in i.content
                                ]
                                if isinstance(i, InputMessage)
                                else [i.item_id]
                                for i in request.request.input
                            ]
                            if isinstance(request.request.input, list)
                            else request.request.input
                        ),
                    )
                )
                span.set_attribute(
                    gen_ai_attributes.GEN_AI_INPUT_MESSAGES,
                    text,
                )
