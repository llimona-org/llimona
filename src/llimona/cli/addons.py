import click


@click.command(name='addons')
def addons():
    from llimona.addons import Addons

    for addon in Addons().list_available():
        click.echo(f'{addon.name}: {addon.display_name} - {addon.description}')
