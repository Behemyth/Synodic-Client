"""Print project version.

Outputs ``version=<pep440>`` line.  In CI this can be appended
directly to ``$GITHUB_OUTPUT``.

Usage examples:
    pdm run version
    pdm run python -m tool.scripts.version
"""

from synodic_client import __version__


def main() -> None:
    """Entry point for the version script."""
    print(f'version={__version__}')


if __name__ == '__main__':
    main()
