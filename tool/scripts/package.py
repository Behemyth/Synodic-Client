"""Packaging script for Spurtle.

Orchestrates PyInstaller + MSIX packaging to produce a complete
release from source.  Invoked via ``pdm run package``.

Usage examples:
    pdm run package
    pdm run package -- --channel stable
    pdm run package -- --local-source D:/releases
"""

import json
import shutil
import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from spurtle import __version__
from tool.scripts.common import OUTPUT_DIR, PACK_DIR, PACK_ID, build, kill_running_instances, run

app = typer.Typer(help='Package Spurtle with PyInstaller and MSIX.')


class Channel(StrEnum):
    """Release channels."""

    dev = 'dev'
    stable = 'stable'


@app.command()
def main(
    *,
    channel: Annotated[Channel, typer.Option(help='Release channel.')] = Channel.dev,
    local_source: Annotated[
        str | None, typer.Option(help='Path to copy releases to (for local dev update testing).')
    ] = None,
    skip_pyinstaller: Annotated[
        bool, typer.Option('--skip-pyinstaller', help='Skip the PyInstaller step (use existing dist/synodic).')
    ] = False,
) -> None:
    """Entry point for the packaging script."""
    print(f'Packaging Spurtle v{__version__} (channel: {channel.value})')

    # Step 1: PyInstaller
    if not skip_pyinstaller:
        build()
    else:
        kill_running_instances()
        print('Skipping PyInstaller (--skip-pyinstaller)')
        if not PACK_DIR.exists():
            print(f'ERROR: Pack directory not found: {PACK_DIR}', file=sys.stderr)
            print('Run without --skip-pyinstaller first.', file=sys.stderr)
            sys.exit(1)

    # Step 1b: Write portable config for dev builds
    if local_source:
        portable_config = {
            'update_source': str(Path(local_source).resolve()),
            'update_channel': channel.value,
        }
        config_path = PACK_DIR / 'config.json'
        config_path.write_text(json.dumps(portable_config, indent=2), encoding='utf-8')
        print(f'Wrote portable config to {config_path}')

    # Step 2: MSIX packaging
    makeappx = shutil.which('makeappx')
    if makeappx is None:
        print('ERROR: makeappx not found. Install the Windows SDK or add it to PATH.', file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    msix_path = OUTPUT_DIR / f'{PACK_ID}-{channel.value}.msix'

    run(
        [
            makeappx,
            'pack',
            '/d',
            str(PACK_DIR),
            '/p',
            str(msix_path),
            '/o',  # overwrite
        ],
        description='Packing with makeappx',
    )

    # Step 3: Sign (optional — signtool must be on PATH)
    signtool = shutil.which('signtool')
    if signtool is not None:
        print('Signing is available but requires a certificate; skipping auto-sign.')
        print(f'  To sign manually: signtool sign /fd SHA256 /a {msix_path}')
    else:
        print('signtool not found — MSIX is unsigned (sideload only).')

    # Step 4: Optionally copy to a local source directory
    if local_source:
        local_path = Path(local_source)
        local_path.mkdir(parents=True, exist_ok=True)
        dest = local_path / msix_path.name
        shutil.copy2(msix_path, dest)
        print(f'Copied MSIX to: {dest}')

    print(f'\nDone! MSIX written to: {msix_path}')
    if local_source:
        print(f'Local update source: {local_source}')


if __name__ == '__main__':
    main()
