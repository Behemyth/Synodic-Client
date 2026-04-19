r"""URI protocol handler registration for the ``spurtle://`` scheme.

MSIX-packaged builds declare ``windows.protocol`` in ``AppxManifest.xml``,
so protocol registration and removal are automatic.  The functions below
are retained only for non-packaged (dev / loose-file) builds where
manual registry manipulation is still required.
"""

import logging
import sys
from typing import Any, cast

logger = logging.getLogger(__name__)

PROTOCOL_NAME = 'spurtle'
LEGACY_PROTOCOL_NAMES = ('synodic',)
_PROTOCOL_DESCRIPTION = 'Spurtle Protocol'
_APPMODEL_ERROR_NO_PACKAGE = 15700


def _registered_protocol_names() -> tuple[str, ...]:
    """Return the protocol names that should be registered for compatibility."""
    if PROTOCOL_NAME == 'spurtle':
        return (PROTOCOL_NAME, *LEGACY_PROTOCOL_NAMES)
    return (PROTOCOL_NAME,)


def _is_msix() -> bool:
    """Return ``True`` when running inside an MSIX package."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes

        windll = ctypes.__dict__.get('windll')
        if windll is None:
            return False
        windll = cast(Any, windll)

        length = ctypes.c_uint32(0)
        result = windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        # APPMODEL_ERROR_NO_PACKAGE means not packaged
        return result != _APPMODEL_ERROR_NO_PACKAGE
    except Exception:
        return False


if sys.platform == 'win32':
    import ctypes
    import winreg

    # Bind RegDeleteTreeW for recursive registry key deletion in a single call.
    _reg_delete_tree = ctypes.windll.advapi32.RegDeleteTreeW
    _reg_delete_tree.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    _reg_delete_tree.restype = ctypes.c_long

    _ERROR_FILE_NOT_FOUND = 2

    def register_protocol(exe_path: str) -> None:
        """Register the ``spurtle://`` URI protocol handler.

        No-op when running inside an MSIX package (the manifest handles it).

        Args:
            exe_path: Absolute path to the application executable.
        """
        if _is_msix():
            logger.debug('MSIX detected — skipping manual protocol registration')
            return

        try:
            for protocol_name in _registered_protocol_names():
                key_path = f'Software\\Classes\\{protocol_name}'
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, _PROTOCOL_DESCRIPTION)
                    winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')

                command_path = f'{key_path}\\shell\\open\\command'
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_path) as key:
                    winreg.SetValueEx(key, '', 0, winreg.REG_SZ, f'"{exe_path}" --uri "%1"')

            logger.info('Registered protocol handlers %s -> %s', _registered_protocol_names(), exe_path)
        except OSError:
            logger.exception('Failed to register protocol handlers %s', _registered_protocol_names())

    def remove_protocol() -> None:
        """Remove the ``spurtle://`` URI protocol handler registration.

        No-op when running inside an MSIX package.
        """
        if _is_msix():
            return

        for protocol_name in _registered_protocol_names():
            key_path = f'Software\\Classes\\{protocol_name}'
            result = _reg_delete_tree(winreg.HKEY_CURRENT_USER, key_path)
            if result == 0:
                logger.info('Removed %s:// protocol handler registration', protocol_name)
            elif result == _ERROR_FILE_NOT_FOUND:
                logger.debug('%s:// protocol handler registration not found, nothing to remove', protocol_name)
            else:
                logger.error('Failed to remove %s:// protocol handler (error code %d)', protocol_name, result)

else:

    def register_protocol(exe_path: str) -> None:
        """Register the ``spurtle://`` URI protocol handler (no-op on non-Windows).

        Args:
            exe_path: Absolute path to the application executable.
        """

    def remove_protocol() -> None:
        """Remove the ``spurtle://`` URI protocol handler registration (no-op on non-Windows)."""


def extract_uri_from_args(args: list[str] | None = None) -> str | None:
    """Return the first supported application URI from *args*, or ``None``.

    Args:
        args: Command-line arguments to scan.  Defaults to
            ``sys.argv[1:]`` when not supplied.
    """
    for a in args if args is not None else sys.argv[1:]:
        lower = a.lower()
        if any(lower.startswith(f'{protocol_name}://') for protocol_name in _registered_protocol_names()):
            return a
    return None
