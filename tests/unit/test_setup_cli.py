"""Tests for the CLI setup subcommands."""

from __future__ import annotations

from dataclasses import field
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip('PySide6.QtWidgets', reason='PySide6 requires system Qt libraries')

from typer.testing import CliRunner

from spurtle.cli import app
from spurtle.schema import ResolvedConfig

runner = CliRunner()


def _make_config(**overrides: object) -> ResolvedConfig:
    from spurtle.schema import DEFAULT_AUTO_UPDATE_INTERVAL_MINUTES, DEFAULT_TOOL_UPDATE_INTERVAL_MINUTES

    defaults: dict[str, object] = {
        'update_source': None,
        'update_channel': 'stable',
        'auto_update_interval_minutes': DEFAULT_AUTO_UPDATE_INTERVAL_MINUTES,
        'tool_update_interval_minutes': DEFAULT_TOOL_UPDATE_INTERVAL_MINUTES,
        'plugin_auto_update': None,
        'prerelease_packages': None,
        'auto_apply': True,
        'auto_start': True,
        'debug_logging': False,
        'last_client_update': None,
        'last_tool_updates': None,
        'setup_profiles': [],
    }
    defaults.update(overrides)
    return ResolvedConfig(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# setup list
# ---------------------------------------------------------------------------


class TestSetupList:
    """Tests for ``sprt setup list``."""

    @staticmethod
    def test_empty() -> None:
        """No profiles prints a message."""
        config = _make_config(setup_profiles=[])
        with patch('spurtle.cli.context.get_services', return_value=(None, MagicMock(), config)):
            result = runner.invoke(app, ['setup', 'list'])
            assert result.exit_code == 0
            assert 'No setup profiles' in result.output

    @staticmethod
    def test_lists_urls() -> None:
        """Configured profiles are printed one per line."""
        config = _make_config(setup_profiles=['https://a.com/p.json', 'https://b.com/p.json'])
        with patch('spurtle.cli.context.get_services', return_value=(None, MagicMock(), config)):
            result = runner.invoke(app, ['setup', 'list'])
            assert result.exit_code == 0
            assert 'https://a.com/p.json' in result.output
            assert 'https://b.com/p.json' in result.output


# ---------------------------------------------------------------------------
# setup add
# ---------------------------------------------------------------------------


class TestSetupAdd:
    """Tests for ``sprt setup add``."""

    @staticmethod
    def test_rejects_http() -> None:
        """Non-HTTPS URLs are rejected."""
        result = runner.invoke(app, ['setup', 'add', 'http://bad.com/p.json'])
        assert result.exit_code == 1

    @staticmethod
    def test_adds_url() -> None:
        """A valid HTTPS URL is appended to the config."""
        mock_user = MagicMock()
        mock_user.setup_profiles = []
        with (
            patch('spurtle.config.load_user_config', return_value=mock_user),
            patch('spurtle.resolution.update_user_config') as mock_update,
        ):
            result = runner.invoke(app, ['setup', 'add', 'https://example.com/p.json'])
            assert result.exit_code == 0
            assert 'Added' in result.output
            mock_update.assert_called_once_with(setup_profiles=['https://example.com/p.json'])

    @staticmethod
    def test_duplicate_url() -> None:
        """Adding a duplicate URL prints a message and does not update."""
        mock_user = MagicMock()
        mock_user.setup_profiles = ['https://example.com/p.json']
        with (
            patch('spurtle.config.load_user_config', return_value=mock_user),
            patch('spurtle.resolution.update_user_config') as mock_update,
        ):
            result = runner.invoke(app, ['setup', 'add', 'https://example.com/p.json'])
            assert result.exit_code == 0
            assert 'already configured' in result.output
            mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# setup remove
# ---------------------------------------------------------------------------


class TestSetupRemove:
    """Tests for ``sprt setup remove``."""

    @staticmethod
    def test_removes_url() -> None:
        """An existing URL is removed from the config."""
        mock_user = MagicMock()
        mock_user.setup_profiles = ['https://example.com/p.json']
        with (
            patch('spurtle.config.load_user_config', return_value=mock_user),
            patch('spurtle.resolution.update_user_config') as mock_update,
        ):
            result = runner.invoke(app, ['setup', 'remove', 'https://example.com/p.json'])
            assert result.exit_code == 0
            assert 'Removed' in result.output
            mock_update.assert_called_once_with(setup_profiles=[])

    @staticmethod
    def test_remove_not_found() -> None:
        """Removing a URL that isn't in the config exits with code 1."""
        mock_user = MagicMock()
        mock_user.setup_profiles = []
        with patch('spurtle.config.load_user_config', return_value=mock_user):
            result = runner.invoke(app, ['setup', 'remove', 'https://example.com/missing.json'])
            assert result.exit_code == 1
            assert 'not found' in result.output


# ---------------------------------------------------------------------------
# setup run
# ---------------------------------------------------------------------------


class TestSetupRun:
    """Tests for ``sprt setup run``."""

    @staticmethod
    def test_rejects_http() -> None:
        """Non-HTTPS profile URLs are rejected."""
        result = runner.invoke(app, ['setup', 'run', 'http://bad.com/p.json'])
        assert result.exit_code == 1
