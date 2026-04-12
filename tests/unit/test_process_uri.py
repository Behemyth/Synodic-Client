"""Tests for _process_uri handling of the setup action."""

from __future__ import annotations

import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

pytest.importorskip('PySide6.QtWidgets', reason='PySide6 requires system Qt libraries')

from synodic_client.application.qt import _process_uri


class TestProcessUriSetup:
    """Tests for the 'setup' action in _process_uri."""

    @staticmethod
    def test_setup_dispatches_profile_url() -> None:
        """A synodic://setup URI should call the setup handler with the profile URL."""
        received: list[str] = []
        _process_uri(
            'synodic://setup?profile=https://example.com/profile.json',
            lambda _m: None,
            received.append,
        )
        assert received == ['https://example.com/profile.json']

    @staticmethod
    def test_setup_without_handler_is_noop() -> None:
        """When setup_handler is None, setup URIs are silently ignored."""
        _process_uri(
            'synodic://setup?profile=https://example.com/profile.json',
            lambda _m: None,
            None,
        )

    @staticmethod
    def test_setup_without_profile_param_is_noop() -> None:
        """A setup URI without a 'profile' query param should not call the handler."""
        received: list[str] = []
        _process_uri(
            'synodic://setup',
            lambda _m: None,
            received.append,
        )
        assert received == []

    @staticmethod
    def test_install_still_works() -> None:
        """Verify install action still dispatches correctly alongside setup."""
        installs: list[str] = []
        setups: list[str] = []
        _process_uri(
            'synodic://install?manifest=https://example.com/m.json',
            installs.append,
            setups.append,
        )
        assert installs == ['https://example.com/m.json']
        assert setups == []
