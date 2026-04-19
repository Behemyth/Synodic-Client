"""Setup profile commands — manage and execute remote setup profiles."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from porringer.api import API

setup_app = typer.Typer(
    help='Manage setup profiles for machine provisioning.',
)


@setup_app.command('run')
def run(
    profile_url: Annotated[
        str,
        typer.Argument(help='HTTPS URL of a setup profile JSON file.'),
    ],
    *,
    json_output: Annotated[
        bool,
        typer.Option('--json', help='Output results as JSON.'),
    ] = False,
) -> None:
    """Resolve a setup profile and install each manifest sequentially."""
    from spurtle.cli.context import get_services

    _, porringer, _ = get_services()

    try:
        asyncio.run(_run_profile(porringer, profile_url, json_output=json_output))
    except (ValueError, RuntimeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


async def _run_profile(porringer: API, profile_url: str, *, json_output: bool) -> None:
    """Resolve and execute all manifests in a profile."""
    from spurtle.cli.progress import make_install_progress
    from spurtle.operations.install import collect_install, open_manifest, open_profile

    async with open_profile(profile_url) as profile:
        if not json_output:
            typer.echo(f'Profile: {profile.name} ({len(profile.manifests)} manifest(s))')

        total_succeeded = 0
        total_failed = 0

        for i, manifest_url in enumerate(profile.manifests, 1):
            if not json_output:
                typer.echo(f'\n[{i}/{len(profile.manifests)}] {manifest_url}')

            async with open_manifest(manifest_url) as manifest_path:
                results = await collect_install(
                    porringer,
                    manifest_path,
                    on_progress=make_install_progress(json_output=json_output),
                )
                succeeded = sum(1 for r in results.results if r.success and not r.skipped)
                failed = sum(1 for r in results.results if not r.success)
                total_succeeded += succeeded
                total_failed += failed
                if not json_output:
                    typer.echo(f'  Done: {succeeded} succeeded, {failed} failed')

    if not json_output:
        typer.echo(f'\nAll done — {total_succeeded} succeeded, {total_failed} failed')


@setup_app.command('list')
def list_profiles() -> None:
    """List saved setup profile URLs."""
    from spurtle.cli.context import get_services

    _, _, config = get_services()
    profiles = config.setup_profiles
    if not profiles:
        typer.echo('No setup profiles configured.')
        return
    for url in profiles:
        typer.echo(url)


@setup_app.command('add')
def add_profile(
    url: Annotated[
        str,
        typer.Argument(help='HTTPS URL of a setup profile JSON file.'),
    ],
) -> None:
    """Add a setup profile URL to the config."""
    from spurtle.operations.install import validate_profile_url
    from spurtle.resolution import update_user_config

    try:
        validate_profile_url(url)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    from spurtle.config import load_user_config

    user = load_user_config()
    existing = list(user.setup_profiles or [])
    if url in existing:
        typer.echo('Profile already configured.')
        return
    existing.append(url)
    update_user_config(setup_profiles=existing)
    typer.echo(f'Added: {url}')


@setup_app.command('remove')
def remove_profile(
    url: Annotated[
        str,
        typer.Argument(help='HTTPS URL of a setup profile to remove.'),
    ],
) -> None:
    """Remove a setup profile URL from the config."""
    from spurtle.config import load_user_config
    from spurtle.resolution import update_user_config

    user = load_user_config()
    existing = list(user.setup_profiles or [])
    if url not in existing:
        typer.echo('Profile not found in config.')
        raise typer.Exit(code=1)
    existing.remove(url)
    update_user_config(setup_profiles=existing)
    typer.echo(f'Removed: {url}')
