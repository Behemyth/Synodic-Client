"""App entrypoint"""
from synodic_client.application.cli import click_cli
from synodic_client.application.gui import qt_application


def cli() -> None:
    """The entrypoint for the command line interface"""
    click_cli()


def gui() -> None:
    """The entrypoint for a gui"""
    qt_application()


if __name__ == "__main__":
    gui()
