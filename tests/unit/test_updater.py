"""Tests for the self-update functionality via .appinstaller (MSIX)."""

from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from spurtle.schema import GITHUB_REPO_URL, UpdateChannel, UpdateConfig, UpdateInfo, UpdateState
from spurtle.updater import Updater

_MODULE = 'spurtle.updater'


@pytest.fixture
def updater() -> Updater:
    """Create an Updater instance for testing."""
    return Updater(current_version=Version('1.0.0'))


@pytest.fixture
def updater_with_config() -> Updater:
    """Create an Updater instance with custom config."""
    config = UpdateConfig(
        repo_url='https://example.com/updates',
        channel=UpdateChannel.DEVELOPMENT,
    )
    return Updater(current_version=Version('1.0.0'), config=config)


class TestUpdateConfig:
    """Tests for UpdateConfig dataclass."""

    @staticmethod
    def test_channel_name_stable() -> None:
        config = UpdateConfig(channel=UpdateChannel.STABLE)
        assert config.channel_name == 'stable'

    @staticmethod
    def test_channel_name_development() -> None:
        config = UpdateConfig(channel=UpdateChannel.DEVELOPMENT)
        assert config.channel_name == 'dev'


class TestUpdater:
    """Tests for Updater class."""

    @staticmethod
    def test_initial_state(updater: Updater) -> None:
        assert updater.state == UpdateState.NO_UPDATE

    @staticmethod
    def test_current_version(updater: Updater) -> None:
        assert updater.current_version == Version('1.0.0')

    @staticmethod
    def test_default_config(updater: Updater) -> None:
        assert updater._config.repo_url == GITHUB_REPO_URL
        assert updater._config.channel == UpdateChannel.STABLE

    @staticmethod
    def test_custom_config(updater_with_config: Updater) -> None:
        assert updater_with_config._config.repo_url == 'https://example.com/updates'
        assert updater_with_config._config.channel == UpdateChannel.DEVELOPMENT

    @staticmethod
    def test_is_installed_when_msix(updater: Updater) -> None:
        with patch(f'{_MODULE}._is_msix', return_value=True):
            assert updater.is_installed is True

    @staticmethod
    def test_is_installed_when_not_msix(updater: Updater) -> None:
        with patch(f'{_MODULE}._is_msix', return_value=False):
            assert updater.is_installed is False


class TestUpdaterCheckForUpdate:
    """Tests for check_for_update method."""

    @staticmethod
    def test_check_not_installed(updater: Updater) -> None:
        with patch(f'{_MODULE}._is_msix', return_value=False):
            info = updater.check_for_update()

        assert info.available is False
        assert info.error is not None
        assert 'MSIX' in info.error

    @staticmethod
    def test_check_no_update(updater: Updater) -> None:
        with (
            patch(f'{_MODULE}._is_msix', return_value=True),
            patch.object(updater, '_check_appinstaller_feed', return_value=Version('1.0.0')),
        ):
            info = updater.check_for_update()

        assert info.available is False
        assert updater.state == UpdateState.NO_UPDATE

    @staticmethod
    def test_check_update_available(updater: Updater) -> None:
        with (
            patch(f'{_MODULE}._is_msix', return_value=True),
            patch.object(updater, '_check_appinstaller_feed', return_value=Version('2.0.0')),
        ):
            info = updater.check_for_update()

        assert info.available is True
        assert info.latest_version == Version('2.0.0')
        assert updater.state == UpdateState.UPDATE_AVAILABLE

    @staticmethod
    def test_check_error(updater: Updater) -> None:
        with (
            patch(f'{_MODULE}._is_msix', return_value=True),
            patch.object(updater, '_check_appinstaller_feed', side_effect=Exception('Network error')),
        ):
            info = updater.check_for_update()

        assert info.available is False
        assert info.error == 'Network error'
        assert updater.state == UpdateState.FAILED

    @staticmethod
    def test_check_feed_returns_none(updater: Updater) -> None:
        """No version extracted from feed -> no update."""
        with (
            patch(f'{_MODULE}._is_msix', return_value=True),
            patch.object(updater, '_check_appinstaller_feed', return_value=None),
        ):
            info = updater.check_for_update()

        assert info.available is False
        assert updater.state == UpdateState.NO_UPDATE

    @staticmethod
    @pytest.mark.parametrize(
        'guarded_state',
        [UpdateState.DOWNLOADING, UpdateState.DOWNLOADED, UpdateState.APPLYING, UpdateState.APPLIED],
        ids=lambda s: s.name.lower(),
    )
    def test_check_preserves_advanced_state(updater: Updater, guarded_state: UpdateState) -> None:
        """Re-checking must not regress advanced states back to UPDATE_AVAILABLE."""
        updater._state = guarded_state

        with (
            patch(f'{_MODULE}._is_msix', return_value=True),
            patch.object(updater, '_check_appinstaller_feed', return_value=Version('2.0.0')),
        ):
            info = updater.check_for_update()

        assert info.available is True
        assert updater.state == guarded_state


class TestUpdaterDownloadUpdate:
    """Tests for download_update method."""

    @staticmethod
    def test_download_not_installed(updater: Updater) -> None:
        with (
            patch(f'{_MODULE}._is_msix', return_value=False),
            pytest.raises(NotImplementedError, match='MSIX'),
        ):
            updater.download_update()

    @staticmethod
    def test_download_no_update_available(updater: Updater) -> None:
        with patch(f'{_MODULE}._is_msix', return_value=True):
            result = updater.download_update()
        assert result is False

    @staticmethod
    def test_download_success(updater: Updater) -> None:
        updater._state = UpdateState.UPDATE_AVAILABLE
        updater._update_info = UpdateInfo(
            available=True,
            current_version=Version('1.0.0'),
            latest_version=Version('2.0.0'),
        )

        with patch(f'{_MODULE}._is_msix', return_value=True):
            result = updater.download_update()

        assert result is True
        assert updater.state == UpdateState.DOWNLOADED

    @staticmethod
    def test_download_calls_progress_callback(updater: Updater) -> None:
        updater._state = UpdateState.UPDATE_AVAILABLE
        updater._update_info = UpdateInfo(
            available=True,
            current_version=Version('1.0.0'),
            latest_version=Version('2.0.0'),
        )
        progress_cb = MagicMock()

        with patch(f'{_MODULE}._is_msix', return_value=True):
            updater.download_update(progress_callback=progress_cb)

        progress_cb.assert_called_once_with(100)


class TestUpdaterApplyUpdate:
    """Tests for apply_update_on_exit."""

    @staticmethod
    def test_apply_not_installed(updater: Updater) -> None:
        with (
            patch(f'{_MODULE}._is_msix', return_value=False),
            pytest.raises(NotImplementedError, match='MSIX'),
        ):
            updater.apply_update_on_exit()

    @staticmethod
    def test_apply_no_downloaded_update(updater: Updater) -> None:
        with (
            patch(f'{_MODULE}._is_msix', return_value=True),
            pytest.raises(RuntimeError, match='No downloaded update'),
        ):
            updater.apply_update_on_exit()

    @staticmethod
    def test_apply_success(updater: Updater) -> None:
        updater._state = UpdateState.DOWNLOADED
        updater._update_info = UpdateInfo(
            available=True,
            current_version=Version('1.0.0'),
            latest_version=Version('2.0.0'),
        )

        with patch(f'{_MODULE}._is_msix', return_value=True):
            updater.apply_update_on_exit(restart=True, silent=True)

        assert updater.state == UpdateState.APPLYING


class TestCheckAppinstallerFeed:
    """Tests for _check_appinstaller_feed."""

    @staticmethod
    def test_parses_version_from_main_bundle(updater: Updater) -> None:
        xml_body = """<?xml version="1.0" encoding="utf-8"?>
        <AppInstaller Uri="https://example.com/synodic.appinstaller" Version="2.1.0">
          <MainBundle Name="synodic" Version="2.1.0" Uri="https://example.com/synodic.msixbundle" />
        </AppInstaller>"""

        mock_resp = MagicMock()
        mock_resp.read.return_value = xml_body.encode('utf-8')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('spurtle.updater.urllib.request.urlopen', return_value=mock_resp):
            version = updater._check_appinstaller_feed()

        assert version == Version('2.1.0')

    @staticmethod
    def test_parses_version_fallback(updater: Updater) -> None:
        """Falls back to first Version attribute when no MainBundle."""
        xml_body = """<?xml version="1.0" encoding="utf-8"?>
        <AppInstaller Uri="https://example.com/synodic.appinstaller" Version="3.0.0">
        </AppInstaller>"""

        mock_resp = MagicMock()
        mock_resp.read.return_value = xml_body.encode('utf-8')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('spurtle.updater.urllib.request.urlopen', return_value=mock_resp):
            version = updater._check_appinstaller_feed()

        assert version == Version('3.0.0')

    @staticmethod
    def test_returns_none_when_no_version(updater: Updater) -> None:
        xml_body = "<AppInstaller></AppInstaller>"

        mock_resp = MagicMock()
        mock_resp.read.return_value = xml_body.encode('utf-8')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('spurtle.updater.urllib.request.urlopen', return_value=mock_resp):
            version = updater._check_appinstaller_feed()

        assert version is None

    @staticmethod
    def test_appends_filename_when_missing(updater: Updater) -> None:
        """When repo_url does not end with .appinstaller, the filename is appended."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'<AppInstaller Version="1.0.0"></AppInstaller>'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('spurtle.updater.urllib.request.urlopen', return_value=mock_resp) as mock_urlopen:
            updater._check_appinstaller_feed()

        req = mock_urlopen.call_args[0][0]
        assert req.full_url.endswith('/synodic.appinstaller')

    @staticmethod
    def test_uses_direct_url_when_appinstaller(updater_with_config: Updater) -> None:
        """When repo_url already ends with .appinstaller, it is used directly."""
        updater_with_config._config = UpdateConfig(
            repo_url='https://example.com/feed.appinstaller',
        )

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'<AppInstaller Version="1.0.0"></AppInstaller>'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('spurtle.updater.urllib.request.urlopen', return_value=mock_resp) as mock_urlopen:
            updater_with_config._check_appinstaller_feed()

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == 'https://example.com/feed.appinstaller'
