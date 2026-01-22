from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

from llimona.cli.utils import pass_app, render, subrender
from llimona.providers import BaseProvider, ProviderModelDesc, ProviderServiceDesc

if TYPE_CHECKING:
    from llimona.app import Llimona


@dataclass
class Arguments:
    provider: str | None = None
    model: str | None = None


pass_provider = click.make_pass_decorator(BaseProvider)  # type: ignore


def render_model(model: ProviderModelDesc, *, indent: str = ' ' * 4) -> Iterable[str]:
    yield model.display_name or model.name
    yield f'{indent}Name: {model.name}'
    if model.allowed_services:
        yield f'{indent}Allowed services:'
        yield from subrender(model.allowed_services, indent=indent + ' ' * 4)


def render_service(service: ProviderServiceDesc, *, indent: str = ' ' * 4) -> Iterable[str]:
    yield service.type


def render_provider(provider: BaseProvider, *, indent: str = ' ' * 4) -> Iterable[str]:
    yield provider.provider.display_name or provider.provider.name
    yield f'{indent}Name: {provider.provider.name}'
    yield f'{indent}Description: {provider.provider.description}'
    if provider.provider.services:
        yield f'{indent}Services:'
        for service in provider.provider.services:
            yield from subrender(render_service(service, indent=indent), indent=indent + ' ' * 4)
    if provider.provider.models:
        yield f'{indent}Models:'
        for model in provider.provider.models:
            yield from subrender(render_model(model, indent=indent), indent=indent + ' ' * 4)


@click.group(name='providers', help='Manage LLM providers', invoke_without_command=True)
@click.argument('provider', type=str, required=False)
@pass_app
@click.pass_context
def providers(ctx: click.Context, app: Llimona, provider: str | None):
    if ctx.invoked_subcommand is not None:
        if provider is None:
            ctx.fail('Provider argument is required when using subcommands.')

        if provider not in app._providers:
            ctx.fail(f'Provider "{provider}" not found.')

        ctx.obj = app._providers[provider]

        return

    if provider is not None:
        if provider not in app._providers:
            ctx.fail(f'Provider "{provider}" not found.')

        render(render_provider(app._providers[provider]))
        return

    for prov in app._providers.values():
        render(render_provider(prov))


@providers.command(name='models', help='List LLM models')
@click.argument('model', type=str, required=False)
@pass_provider
def providers_models(provider: BaseProvider, model: str | None):
    if model is not None:
        render(render_model(provider.provider.models[model]))
        return

    for prov in provider.provider.models:
        render(render_model(prov))
