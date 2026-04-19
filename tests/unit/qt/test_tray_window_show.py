"""Tests that the tray only brings the window to the front on manual actions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QSystemTrayIcon

from spurtle.application.screen.schema import UpdateTarget
from spurtle.application.screen.tray import TrayScreen
from spurtle.operations.schema import UpdateResult

from .conftest import make_config_store


@pytest.fixture
def tray_screen():
    """Build a minimal ``TrayScreen`` with mocked collaborators."""
    with (
        patch('spurtle.application.screen.tool_update_controller.resolve_update_config') as mock_ucfg,
        patch('spurtle.application.screen.tray.UpdateController'),
    ):
        # Disable timers by setting intervals to 0
        mock_ucfg.return_value = MagicMock(
            auto_update_interval_minutes=0,
            tool_update_interval_minutes=0,
        )

        app = MagicMock()
        client = MagicMock()
        window = MagicMock()
        store = make_config_store()
        with patch('spurtle.application.screen.tray.SettingsWindow'):
            ts = TrayScreen(app, client, window, store=store)

        return ts


class TestToolUpdateWindowShow:
    """_on_tool_update_finished should only show the window for manual updates."""

    @staticmethod
    def test_auto_update_does_not_show_window(tray_screen) -> None:
        """Periodic (automatic) tool update must not bring the window forward."""
        result = UpdateResult(manifests_processed=1, packages_updated=['pkg'])
        tray_screen._tool_orchestrator._on_tool_update_finished(result)
        tray_screen._window.show.assert_not_called()

    @staticmethod
    def test_manual_plugin_update_shows_window(tray_screen) -> None:
        """A user-initiated single-plugin update should show the window."""
        result = UpdateResult(manifests_processed=1, packages_updated=['pkg'])
        tray_screen._tool_orchestrator._on_tool_update_finished(result, UpdateTarget(plugin='pipx'))
        tray_screen._window.show.assert_called_once()

    @staticmethod
    def test_manual_package_update_shows_window(tray_screen) -> None:
        """A user-initiated single-package update should show the window."""
        result = UpdateResult(manifests_processed=1, packages_updated=['pkg'])
        tray_screen._tool_orchestrator._on_tool_update_finished(
            result,
            UpdateTarget(plugin='pipx', package='ruff'),
        )
        tray_screen._window.show.assert_called_once()

    @staticmethod
    def test_auto_update_with_no_changes_does_not_show(tray_screen) -> None:
        """An automatic check with nothing to update must stay hidden."""
        result = UpdateResult(manifests_processed=1, already_latest=['pkg'])
        tray_screen._tool_orchestrator._on_tool_update_finished(result)
        tray_screen._window.show.assert_not_called()


class TestTrayActivation:
    """_on_tray_activated should dispatch correctly by reason."""

    @staticmethod
    def test_double_click_shows_window(tray_screen) -> None:
        """Double-clicking the tray icon should show and raise the window."""
        tray_screen._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
        tray_screen._window.show.assert_called_once()
        tray_screen._window.raise_.assert_called_once()
        tray_screen._window.activateWindow.assert_called_once()

    @staticmethod
    def test_context_does_not_show_window_or_call_timer(tray_screen) -> None:
        """Right-clicking is handled by setContextMenu, so _on_tray_activated is a no-op."""
        tray_screen._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
        tray_screen._window.show.assert_not_called()

    @staticmethod
    def test_context_does_not_show_window(tray_screen) -> None:
        """Right-clicking should not bring the main window forward."""
        tray_screen._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
        tray_screen._window.show.assert_not_called()
