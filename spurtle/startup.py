r"""Windows auto-startup management.

MSIX-packaged builds declare a ``windows.startupTask`` in
``AppxManifest.xml``; the OS manages the startup entry.  The functions
below fall back to manual registry manipulation only for non-packaged
(dev / loose-file) builds.

For non-MSIX builds, a value is written under
``HKCU\Software\Microsoft\Windows\CurrentVersion\Run`` alongside an
enabled flag in ``StartupApproved\Run``.

Other platforms are stubbed with no-op implementations, matching the
approach in :mod:`spurtle.protocol`.
"""

import logging
import sys

logger = logging.getLogger(__name__)

STARTUP_VALUE_NAME = 'SynodicClient'
"""Registry value name used in the ``Run`` key."""

RUN_KEY_PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'

STARTUP_APPROVED_KEY_PATH = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'
"""Registry key where Windows stores per-entry enabled/disabled flags."""

# 12-byte REG_BINARY payloads for the StartupApproved value.
APPROVED_ENABLED: bytes = b'\x02' + b'\x00' * 11
"""Enabled payload for the ``StartupApproved\\Run`` registry value."""

_APPROVED_DISABLED_BYTE: int = 0x03


def _is_msix() -> bool:
    """Return ``True`` when running inside an MSIX package."""
    from spurtle.protocol import _is_msix as _check

    return _check()


if sys.platform == 'win32':
    import winreg

    def register_startup(exe_path: str) -> None:
        r"""Register the application to start automatically on login.

        No-op when running inside an MSIX package.

        Args:
            exe_path: Absolute path to the application executable.
        """
        if _is_msix():
            logger.debug('MSIX detected — skipping manual startup registration')
            return

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
            logger.info('Registered auto-startup -> %s', exe_path)
        except OSError:
            logger.exception('Failed to register auto-startup')

        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY_PATH) as key:
                winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_BINARY, APPROVED_ENABLED)
            logger.debug('Wrote StartupApproved enabled flag')
        except OSError:
            logger.exception('Failed to write StartupApproved enabled flag')

    def remove_startup() -> None:
        """Remove the auto-startup registration.

        No-op when running inside an MSIX package.
        """
        if _is_msix():
            logger.debug('MSIX detected — skipping manual startup removal')
            return

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            logger.info('Removed auto-startup registration')
        except FileNotFoundError:
            logger.debug('Auto-startup registration not found, nothing to remove')
        except OSError:
            logger.exception('Failed to remove auto-startup registration')

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            logger.debug('Removed StartupApproved flag')
        except FileNotFoundError:
            logger.debug('StartupApproved flag not found, nothing to remove')
        except OSError:
            logger.exception('Failed to remove StartupApproved flag')

    def get_registered_startup_path() -> str | None:
        r"""Return the executable path stored in the ``Run`` registry key.

        Returns ``None`` when running as MSIX (startup is managed by the OS).
        """
        if _is_msix():
            return None

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
                value, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
                return value.strip('"') if isinstance(value, str) else None
        except FileNotFoundError:
            return None
        except OSError:
            logger.exception('Failed to read auto-startup path from registry')
            return None

    def is_startup_registered() -> bool:
        r"""Check whether auto-startup is both present **and** enabled.

        Under MSIX, always returns ``True`` (the OS manages the startup
        task declaratively).
        """
        if _is_msix():
            return True

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
                winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
        except FileNotFoundError:
            return False
        except OSError:
            logger.exception('Failed to query auto-startup registration')
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
                data, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
                if isinstance(data, bytes) and len(data) >= 1 and data[0] == _APPROVED_DISABLED_BYTE:
                    logger.debug('Auto-startup is disabled via StartupApproved')
                    return False
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception('Failed to query StartupApproved flag')

        return True

else:

    def register_startup(exe_path: str) -> None:
        """Register auto-startup (no-op on non-Windows).

        Args:
            exe_path: Absolute path to the application executable.
        """

    def remove_startup() -> None:
        """Remove auto-startup registration (no-op on non-Windows)."""

    def get_registered_startup_path() -> str | None:
        """Return the registered startup path (always ``None`` on non-Windows)."""
        return None

    def is_startup_registered() -> bool:
        """Check auto-startup registration (always ``False`` on non-Windows)."""
        return False


def sync_startup(exe_path: str, *, auto_start: bool) -> None:
    """Synchronise the auto-startup state with the given preference.

    Under MSIX this is a no-op (the startup task is declared in the
    manifest and toggled by the OS).  For non-packaged builds it
    registers or removes the startup entry.

    Args:
        exe_path: Absolute path to the application executable.
        auto_start: Whether auto-startup should be enabled.
    """
    if not getattr(sys, 'frozen', False):
        return

    if _is_msix():
        logger.debug('MSIX detected — startup task managed by OS, skipping sync')
        return

    if auto_start:
        register_startup(exe_path)
    else:
        remove_startup()
