import asyncio
from pathlib import Path

import click

from llimona.cli.addons import addons
from llimona.cli.openai import openai
from llimona.cli.providers import providers


@click.group
@click.option('--log-stdout', is_flag=True, help='Enable logging to stdout')
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    help='Set the logging level',
    default='INFO',
)
@click.pass_context
def llimona(ctx: click.Context, log_stdout: bool, log_level: str):
    """Main entry point for the Llimona CLI."""

    from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, StreamHandler, basicConfig, getLogger

    level = {
        'DEBUG': DEBUG,
        'INFO': INFO,
        'WARNING': WARNING,
        'ERROR': ERROR,
        'CRITICAL': CRITICAL,
    }[log_level]

    basicConfig(level=level, format='%(asctime)s - %(created).6f - %(name)s - %(levelname)s - %(message)s')

    if log_stdout:
        logger = getLogger()
        logger.addHandler(StreamHandler())


@llimona.group(invoke_without_command=True)
@click.option(
    '--config-file', type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path), required=True
)
@click.pass_context
def app(ctx: click.Context, config_file: Path):
    """
    Main entry point for running a Llimona application.
    The application is configured using a YAML file specified by the --config-file option.
    """
    import yaml

    from ..config.app import AppBuilder, AppConfig
    from ..config.yaml import ConfigLoader

    config = AppConfig.model_validate(
        yaml.load(config_file.read_text(), Loader=ConfigLoader.with_cwd(config_file.parent))
    )

    ctx.obj = asyncio.run(AppBuilder(config).build())

    if ctx.invoked_subcommand is None:
        ctx.fail('Missing command.')


app.add_command(openai)
app.add_command(providers)
llimona.add_command(addons)

if __name__ == '__main__':
    llimona()
