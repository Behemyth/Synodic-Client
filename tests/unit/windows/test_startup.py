"""Tests for Windows auto-startup registration."""

import winreg
from unittest.mock import MagicMock, patch

import pytest

from spurtle.startup import (
    APPROVED_ENABLED,
    RUN_KEY_PATH,
    STARTUP_APPROVED_KEY_PATH,
    STARTUP_VALUE_NAME,
    get_registered_startup_path,
    is_startup_registered,
    register_startup,
    remove_startup,
    sync_startup,
)

from .conftest import make_registry_key

_MSIX_PATCH = 'spurtle.startup._is_msix'


@pytest.fixture(autouse=True)
def _not_msix():
    """Default all tests to non-MSIX mode."""
    with patch(_MSIX_PATCH, return_value=False):
        yield


class TestRegisterStartup:
    @staticmethod
    def test_writes_registry_value() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key) as mock_open,
            patch.object(winreg, 'SetValueEx') as mock_set,
            patch.object(winreg, 'CreateKey', return_value=mock_key),
        ):
            register_startup(r'C:\Program Files\Synodic\synodic.exe')
        mock_open.assert_called_once_with(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        mock_set.assert_any_call(
            mock_key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, r'"C:\Program Files\Synodic\synodic.exe"'
        )

    @staticmethod
    def test_writes_startup_approved_enabled() -> None:
        mock_run_key = make_registry_key()
        mock_approved_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_run_key),
            patch.object(winreg, 'SetValueEx') as mock_set,
            patch.object(winreg, 'CreateKey', return_value=mock_approved_key) as mock_create,
        ):
            register_startup(r'C:\synodic.exe')
        mock_create.assert_called_once_with(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY_PATH)
        mock_set.assert_any_call(mock_approved_key, STARTUP_VALUE_NAME, 0, winreg.REG_BINARY, APPROVED_ENABLED)

    @staticmethod
    def test_noop_when_msix() -> None:
        with (
            patch(_MSIX_PATCH, return_value=True),
            patch.object(winreg, 'OpenKey') as mock_open,
        ):
            register_startup(r'C:\synodic.exe')
        mock_open.assert_not_called()


class TestRemoveStartup:
    @staticmethod
    def test_deletes_registry_value() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(winreg, 'DeleteValue') as mock_delete,
        ):
            remove_startup()
        mock_delete.assert_any_call(mock_key, STARTUP_VALUE_NAME)

    @staticmethod
    def test_clears_startup_approved() -> None:
        mock_run_key = make_registry_key()
        mock_approved_key = make_registry_key()

        def _open_key_side_effect(_root, path, _reserved, _access):
            if 'Explorer' in path:
                return mock_approved_key
            return mock_run_key

        with (
            patch.object(winreg, 'OpenKey', side_effect=_open_key_side_effect),
            patch.object(winreg, 'DeleteValue') as mock_delete,
        ):
            remove_startup()
        assert mock_delete.call_count == 2
        mock_delete.assert_any_call(mock_run_key, STARTUP_VALUE_NAME)
        mock_delete.assert_any_call(mock_approved_key, STARTUP_VALUE_NAME)

    @staticmethod
    def test_handles_missing_value_gracefully() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(winreg, 'DeleteValue', side_effect=FileNotFoundError),
        ):
            remove_startup()

    @staticmethod
    def test_noop_when_msix() -> None:
        with (
            patch(_MSIX_PATCH, return_value=True),
            patch.object(winreg, 'OpenKey') as mock_open,
        ):
            remove_startup()
        mock_open.assert_not_called()


class TestIsStartupRegistered:
    @staticmethod
    def test_returns_true_when_present() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(
                winreg,
                'QueryValueEx',
                side_effect=[
                    (r'"C:\synodic.exe"', winreg.REG_SZ),
                    FileNotFoundError,
                ],
            ),
        ):
            assert is_startup_registered() is True

    @staticmethod
    def test_returns_true_when_startup_approved_enabled() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(
                winreg,
                'QueryValueEx',
                side_effect=[
                    (r'"C:\synodic.exe"', winreg.REG_SZ),
                    (b'\x02' + b'\x00' * 11, winreg.REG_BINARY),
                ],
            ),
        ):
            assert is_startup_registered() is True

    @staticmethod
    def test_returns_false_when_startup_approved_disabled() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(
                winreg,
                'QueryValueEx',
                side_effect=[
                    (r'"C:\synodic.exe"', winreg.REG_SZ),
                    (b'\x03' + b'\x00' * 11, winreg.REG_BINARY),
                ],
            ),
        ):
            assert is_startup_registered() is False

    @staticmethod
    def test_returns_false_when_missing() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(winreg, 'QueryValueEx', side_effect=FileNotFoundError),
        ):
            assert is_startup_registered() is False

    @staticmethod
    def test_returns_true_when_msix() -> None:
        with patch(_MSIX_PATCH, return_value=True):
            assert is_startup_registered() is True


class TestGetRegisteredStartupPath:
    @staticmethod
    def test_returns_unquoted_path() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(
                winreg, 'QueryValueEx', return_value=(r'"C:\Program Files\Synodic\synodic.exe"', winreg.REG_SZ)
            ),
        ):
            assert get_registered_startup_path() == r'C:\Program Files\Synodic\synodic.exe'

    @staticmethod
    def test_returns_none_when_missing() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(winreg, 'QueryValueEx', side_effect=FileNotFoundError),
        ):
            assert get_registered_startup_path() is None

    @staticmethod
    def test_returns_none_on_os_error() -> None:
        mock_key = make_registry_key()
        with (
            patch.object(winreg, 'OpenKey', return_value=mock_key),
            patch.object(winreg, 'QueryValueEx', side_effect=OSError('access denied')),
        ):
            assert get_registered_startup_path() is None

    @staticmethod
    def test_returns_none_when_msix() -> None:
        with patch(_MSIX_PATCH, return_value=True):
            assert get_registered_startup_path() is None


_SYNC_MODULE = 'spurtle.startup'


class TestSyncStartup:
    @staticmethod
    def test_registers_when_auto_start_true() -> None:
        with (
            patch(f'{_SYNC_MODULE}.getattr', return_value=True),
            patch(f'{_SYNC_MODULE}.register_startup') as mock_reg,
            patch(f'{_SYNC_MODULE}.remove_startup') as mock_rem,
        ):
            sync_startup(r'C:\app\synodic.exe', auto_start=True)
        mock_reg.assert_called_once_with(r'C:\app\synodic.exe')
        mock_rem.assert_not_called()

    @staticmethod
    def test_removes_when_auto_start_false() -> None:
        with (
            patch(f'{_SYNC_MODULE}.getattr', return_value=True),
            patch(f'{_SYNC_MODULE}.register_startup') as mock_reg,
            patch(f'{_SYNC_MODULE}.remove_startup') as mock_rem,
        ):
            sync_startup(r'C:\app\synodic.exe', auto_start=False)
        mock_rem.assert_called_once()
        mock_reg.assert_not_called()

    @staticmethod
    def test_noop_when_not_frozen() -> None:
        with (
            patch(f'{_SYNC_MODULE}.getattr', return_value=False),
            patch(f'{_SYNC_MODULE}.register_startup') as mock_reg,
            patch(f'{_SYNC_MODULE}.remove_startup') as mock_rem,
        ):
            sync_startup(r'C:\app\synodic.exe', auto_start=True)
        mock_reg.assert_not_called()
        mock_rem.assert_not_called()

    @staticmethod
    def test_noop_when_msix() -> None:
        with (
            patch(f'{_SYNC_MODULE}.getattr', return_value=True),
            patch(_MSIX_PATCH, return_value=True),
            patch(f'{_SYNC_MODULE}.register_startup') as mock_reg,
            patch(f'{_SYNC_MODULE}.remove_startup') as mock_rem,
        ):
            sync_startup(r'C:\app\synodic.exe', auto_start=True)
        mock_reg.assert_not_called()
        mock_rem.assert_not_called()
