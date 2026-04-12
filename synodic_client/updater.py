"""Self-update functionality via .appinstaller (MSIX).

For MSIX-packaged builds the OS manages update discovery and
installation through the ``.appinstaller`` file declared at install
time.  This module provides a thin wrapper that checks the
``.appinstaller`` feed URL for a newer version and exposes the same
check / download / apply lifecycle that the rest of the codebase expects.

For non-packaged (development) builds, updates are not supported.
"""

import logging
import re
import sys
import urllib.request
from collections.abc import Callable

from packaging.version import Version

from synodic_client.protocol import _is_msix
from synodic_client.schema import (
    UpdateConfig,
    UpdateInfo,
    UpdateState,
)

logger = logging.getLogger(__name__)


class Updater:
    """Handles self-update operations via .appinstaller feeds."""

    def __init__(self, current_version: Version, config: UpdateConfig | None = None) -> None:
        """Initialize the updater.

        Args:
            current_version: The current version of the application.
            config: Update configuration, uses defaults if not provided.
        """
        self._current_version = current_version
        self._config = config or UpdateConfig()
        self._state = UpdateState.NO_UPDATE
        self._update_info: UpdateInfo | None = None

        logger.info(
            'Updater created: version=%s, channel=%s, source=%s',
            self._current_version,
            self._config.channel_name,
            self._config.repo_url,
        )

    @property
    def current_version(self) -> Version:
        """Best-known application version."""
        return self._current_version

    @property
    def state(self) -> UpdateState:
        """Current state of the update process."""
        return self._state

    @property
    def is_installed(self) -> bool:
        """Return True when running as an MSIX-packaged application."""
        return _is_msix()

    def check_for_update(self) -> UpdateInfo:
        """Check for available updates via the .appinstaller feed.

        Returns:
            UpdateInfo with details about available updates.
        """
        if not self.is_installed:
            logger.info('Not an MSIX install, skipping update check')
            return UpdateInfo(
                available=False,
                current_version=self._current_version,
                error='Not installed as MSIX package',
            )

        try:
            latest = self._check_appinstaller_feed()

            if latest is not None and latest > self._current_version:
                self._update_info = UpdateInfo(
                    available=True,
                    current_version=self._current_version,
                    latest_version=latest,
                )
                if self._state not in {
                    UpdateState.DOWNLOADING,
                    UpdateState.DOWNLOADED,
                    UpdateState.APPLYING,
                    UpdateState.APPLIED,
                }:
                    self._state = UpdateState.UPDATE_AVAILABLE
                logger.info('Update available: %s -> %s', self._current_version, latest)
            else:
                self._update_info = UpdateInfo(
                    available=False,
                    current_version=self._current_version,
                )
                self._state = UpdateState.NO_UPDATE
                logger.info('No update available, current version: %s', self._current_version)

            return self._update_info

        except Exception as e:
            logger.exception('Failed to check for updates')
            self._state = UpdateState.FAILED
            return UpdateInfo(
                available=False,
                current_version=self._current_version,
                error=str(e),
            )

    def _check_appinstaller_feed(self) -> Version | None:
        """Fetch the .appinstaller XML and extract the latest version.

        Returns:
            The latest version advertised in the feed, or None.
        """
        feed_url = self._config.repo_url.rstrip('/')
        if not feed_url.endswith('.appinstaller'):
            feed_url = f'{feed_url}/synodic.appinstaller'

        logger.debug('Checking appinstaller feed: %s', feed_url)

        req = urllib.request.Request(feed_url, headers={'User-Agent': 'synodic-client'})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            body = resp.read().decode('utf-8')

        # Parse Version attribute from the AppInstaller XML.
        match = re.search(r'<MainBundle[^>]+Version="([^"]+)"', body)
        if match is None:
            match = re.search(r'Version="([^"]+)"', body)
        if match is None:
            logger.warning('Could not extract version from appinstaller feed')
            return None

        return Version(match.group(1))

    def download_update(self, progress_callback: Callable[[int], None] | None = None) -> bool:
        """Signal that the update is ready.

        Under MSIX the OS handles the actual download.  This method
        transitions the state machine so the controller can proceed
        to the apply step.

        Returns:
            True when an update is staged.
        """
        if not self.is_installed:
            raise NotImplementedError('Updates are only supported for MSIX installs')

        if self._state != UpdateState.UPDATE_AVAILABLE or not self._update_info:
            logger.error('No update available to download')
            return False

        self._state = UpdateState.DOWNLOADED
        logger.info('Update marked as ready (OS handles download)')

        if progress_callback is not None:
            progress_callback(100)

        return True

    def apply_update_on_exit(
        self,
        restart: bool = True,
        silent: bool = False,
        restart_args: list[str] | None = None,
    ) -> None:
        """Request the OS to apply the pending MSIX update.

        The Windows Store / .appinstaller subsystem applies the update
        when the application exits.  This method is a state-transition
        marker; the caller is responsible for quitting the process.
        """
        if not self.is_installed:
            raise NotImplementedError('Updates are only supported for MSIX installs')

        if self._state != UpdateState.DOWNLOADED or not self._update_info:
            raise RuntimeError('No downloaded update to apply')

        logger.info('Staging MSIX update (restart=%s, silent=%s)', restart, silent)
        self._state = UpdateState.APPLYING
