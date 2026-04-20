import asyncio
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING

import click

from llimona.cli.utils import pass_app

if TYPE_CHECKING:
    from llimona.app import Llimona


@click.group(name='openai')
def openai():
    """Group for OpenAI-related commands."""
    pass


@openai.group(name='responses')
def responses():
    """Group for OpenAI response-related commands."""
    pass


@responses.command(name='create')
@click.argument('model', type=str, required=True)
@click.argument('prompt', type=str, required=True)
@click.option('--stream', is_flag=True)
@pass_app
def responses_create(app: Llimona, model: str, prompt: str, stream: bool):
    """Create a response using the OpenAI provider interface."""

    async def action():
        from llimona.interfaces.openai.models.api_responses import CreateResponse

        ctx = app.build_context(None)
        result = await app.openai_responses.create(
            CreateResponse.model_validate({'model': model, 'input': prompt, 'stream': stream}), parent_ctx=ctx
        )
        if isinstance(result, AsyncIterable):
            async for event in result:
                click.echo(event)
        else:
            click.echo(result)

        for sensor_value in ctx.get_sensor_values():
            click.echo(
                f'Sensor value: {sensor_value.name}={sensor_value.value}'
                + (f' ({sensor_value.description})' if sensor_value.description else '')
            )

    asyncio.run(action())


@openai.group(name='models')
def models():
    """Group for OpenAI model-related commands."""
    pass


@models.command(name='list')
@click.argument('provider', type=str, required=False)
@click.option(
    '--actor-id',
    type=str,
    required=False,
    help='Actor ID to use for listing models. If not provided, a default actor ID will be used.',
)
@click.option(
    '--remote',
    is_flag=True,
    help='Whether to fetch the model list from the remote provider instead of using cached data',
)
@pass_app
def models_list(app: Llimona, provider: str | None = None, actor_id: str | None = None, remote: bool = False):
    """List OpenAI models using the OpenAI provider interface."""

    async def action():
        async for model in app.openai_models.list(provider_name=provider, remote=remote):
            click.echo(model)

    asyncio.run(action())
