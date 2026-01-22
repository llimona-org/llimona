from collections.abc import Iterable

import click

from llimona.app import Llimona

pass_app = click.make_pass_decorator(Llimona)


def subrender(renderable: str | Iterable[str], indent: str = '') -> Iterable[str]:
    if isinstance(renderable, str):
        yield f'{indent}{renderable}'
    else:
        for line in renderable:
            yield f'{indent}{line}'


def render(renderable: str | Iterable[str], indent: str = '') -> None:
    for line in renderable:
        click.echo(line)
