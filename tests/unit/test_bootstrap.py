"""Tests for the bootstrap entry point."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

_MODULE = 'synodic_client.application.bootstrap'


def _run_bootstrap(*, argv: list[str]) -> None:
    """Import (or reload) the bootstrap module, triggering ``bootstrap()``.

    The module-level ``bootstrap()`` call runs on every import/reload,
    so all patches must be in place before calling this.
    """
    with patch.object(sys, 'argv', argv):
        if _MODULE in sys.modules:
            importlib.reload(sys.modules[_MODULE])
        else:
            importlib.import_module(_MODULE)


class TestBootstrapSequence:
    """Verify the bootstrap sequence invokes the expected helpers."""

    @staticmethod
    def test_preamble_called_in_production_mode() -> None:
        """run_startup_preamble is called when --dev is absent."""
        with (
            patch('synodic_client.config.set_dev_mode'),
            patch('synodic_client.logging.configure_logging'),
            patch('synodic_client.subprocess_patch.apply'),
            patch('synodic_client.application.init.run_startup_preamble') as mock_preamble,
            patch('synodic_client.application.qt.application'),
            patch('synodic_client.protocol.extract_uri_from_args', return_value=None),
        ):
            _run_bootstrap(argv=[r'C:\app\synodic.exe'])

        mock_preamble.assert_called_once_with(sys.executable)

    @staticmethod
    def test_preamble_skipped_in_dev_mode() -> None:
        """run_startup_preamble is not called when --dev flag is passed."""
        with (
            patch('synodic_client.config.set_dev_mode'),
            patch('synodic_client.logging.configure_logging'),
            patch('synodic_client.subprocess_patch.apply'),
            patch('synodic_client.application.init.run_startup_preamble') as mock_preamble,
            patch('synodic_client.application.qt.application'),
            patch('synodic_client.protocol.extract_uri_from_args', return_value=None),
        ):
            _run_bootstrap(argv=[r'C:\app\synodic.exe', '--dev'])

        mock_preamble.assert_not_called()
