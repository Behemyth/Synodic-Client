"""CLI entry point for the Spurtle application.

Restructured as a package with resource-verb subcommands:

    sprt                    → launch GUI
    sprt project list       → list cached projects
    sprt tool check         → check for tool updates
    sprt config get <key>   → read a config value
    sprt update check       → check for self-update
    sprt debug state        → dump running instance state (IPC)
"""

from typing import Annotated

import typer
from spurtle import __version__
from spurtle.cli.config import config_app
from spurtle.cli.debug import debug_app
from spurtle.cli.install import install
from spurtle.cli.project import project_app
from spurtle.cli.setup import setup_app
from spurtle.cli.tool import tool_app
from spurtle.cli.update import update_app

app = typer.Typer(
    name='sprt',
    help='Spurtle — a system tray frontend for porringer.',
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        typer.echo(f'spurtle {__version__}')
        raise typer.Exit


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    *,
    uri: Annotated[
        str | None,
        typer.Option('--uri', help='A spurtle:// URI to process on launch.'),
    ] = None,
    version: Annotated[
        bool | None,
        typer.Option('--version', callback=_version_callback, is_eager=True, help='Show version and exit.'),
    ] = None,
    dev: Annotated[
        bool,
        typer.Option('--dev', help='Run in dev mode with isolated config, logs, and instance lock.'),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option('--debug', help='Enable DEBUG-level file logging for this session.'),
    ] = False,
) -> None:
    """Launch the Spurtle GUI application."""
    if ctx.invoked_subcommand is not None:
        return

    from spurtle.application.qt import application

    application(uri=uri, dev_mode=dev, debug=debug)


# -- Register sub-typers --------------------------------------------------

app.add_typer(project_app, name='project')
app.add_typer(tool_app, name='tool')
app.command('install')(install)
app.add_typer(config_app, name='config')
app.add_typer(update_app, name='update')
app.add_typer(debug_app, name='debug')
app.add_typer(setup_app, name='setup')
