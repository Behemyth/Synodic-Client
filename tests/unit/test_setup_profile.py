"""Tests for setup profile validation, schema, and resolution."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from synodic_client.operations.install import resolve_profile, validate_profile_url
from synodic_client.operations.schema import SetupProfile

# ---------------------------------------------------------------------------
# validate_profile_url
# ---------------------------------------------------------------------------


class TestValidateProfileUrl:
    """Tests for the HTTPS-only URL validator."""

    @staticmethod
    def test_accepts_https() -> None:
        """An HTTPS URL should pass without error."""
        validate_profile_url('https://example.com/profile.json')

    @staticmethod
    def test_rejects_http() -> None:
        """An HTTP URL must be rejected."""
        with pytest.raises(ValueError, match='Only HTTPS'):
            validate_profile_url('http://example.com/profile.json')

    @staticmethod
    def test_rejects_ftp() -> None:
        """An FTP URL must be rejected."""
        with pytest.raises(ValueError, match='Only HTTPS'):
            validate_profile_url('ftp://example.com/profile.json')

    @staticmethod
    def test_rejects_bare_path() -> None:
        """A bare filesystem path must be rejected."""
        with pytest.raises(ValueError, match='Only HTTPS'):
            validate_profile_url('/tmp/profile.json')

    @staticmethod
    def test_rejects_empty_string() -> None:
        """An empty string must be rejected."""
        with pytest.raises(ValueError, match='Only HTTPS'):
            validate_profile_url('')

    @staticmethod
    def test_rejects_file_scheme() -> None:
        """A file:// URL must be rejected."""
        with pytest.raises(ValueError, match='Only HTTPS'):
            validate_profile_url('file:///tmp/profile.json')


# ---------------------------------------------------------------------------
# SetupProfile model
# ---------------------------------------------------------------------------


class TestSetupProfileModel:
    """Tests for the Pydantic SetupProfile schema."""

    @staticmethod
    def test_valid_profile() -> None:
        """A well-formed dict should parse into a SetupProfile."""
        data = {
            'version': '1',
            'name': 'My Profile',
            'manifests': ['https://example.com/a.json', 'https://example.com/b.json'],
        }
        profile = SetupProfile.model_validate(data)
        assert profile.version == '1'
        assert profile.name == 'My Profile'
        assert len(profile.manifests) == 2

    @staticmethod
    def test_missing_name_raises() -> None:
        """Omitting 'name' should raise a validation error."""
        data = {'version': '1', 'manifests': []}
        with pytest.raises(Exception):
            SetupProfile.model_validate(data)

    @staticmethod
    def test_missing_version_raises() -> None:
        """Omitting 'version' should raise a validation error."""
        data = {'name': 'P', 'manifests': []}
        with pytest.raises(Exception):
            SetupProfile.model_validate(data)

    @staticmethod
    def test_empty_manifests_list() -> None:
        """An empty manifests list should be valid."""
        profile = SetupProfile.model_validate({'version': '1', 'name': 'P', 'manifests': []})
        assert profile.manifests == []


# ---------------------------------------------------------------------------
# resolve_profile
# ---------------------------------------------------------------------------


class TestResolveProfile:
    """Tests for downloading and parsing a remote setup profile."""

    @staticmethod
    def test_rejects_non_https() -> None:
        """resolve_profile should reject non-HTTPS URLs."""
        with pytest.raises(ValueError, match='Only HTTPS'):
            asyncio.run(resolve_profile('http://example.com/profile.json'))

    @staticmethod
    def test_download_failure_raises_runtime_error() -> None:
        """A failed download should raise RuntimeError."""
        mock_result = MagicMock(success=False, message='timeout')
        with (
            patch('synodic_client.operations.install.DownloadParameters'),
            patch('porringer.api.API.download', new_callable=AsyncMock, return_value=mock_result),
        ):
            with pytest.raises(RuntimeError, match='Failed to download profile'):
                asyncio.run(resolve_profile('https://example.com/profile.json'))

    @staticmethod
    def test_invalid_json_raises_runtime_error(tmp_path: Path) -> None:
        """Malformed JSON should raise RuntimeError."""

        async def fake_download(params: object) -> MagicMock:
            dest = params.destination  # type: ignore[attr-defined]
            dest.write_text('not json', encoding='utf-8')
            return MagicMock(success=True)

        with (
            patch('porringer.api.API.download', side_effect=fake_download),
            patch('tempfile.mkdtemp', return_value=str(tmp_path)),
            patch('synodic_client.operations.install.safe_rmtree'),
        ):
            with pytest.raises(RuntimeError, match='Failed to parse profile'):
                asyncio.run(resolve_profile('https://example.com/profile.json'))

    @staticmethod
    def test_manifest_url_validation(tmp_path: Path) -> None:
        """Manifest URLs inside the profile must be HTTPS."""
        profile_data = {
            'version': '1',
            'name': 'Bad',
            'manifests': ['http://evil.com/manifest.json'],
        }

        async def fake_download(params: object) -> MagicMock:
            dest = params.destination  # type: ignore[attr-defined]
            dest.write_text(json.dumps(profile_data), encoding='utf-8')
            return MagicMock(success=True)

        with (
            patch('porringer.api.API.download', side_effect=fake_download),
            patch('tempfile.mkdtemp', return_value=str(tmp_path)),
        ):
            with pytest.raises(ValueError, match='Only HTTPS'):
                asyncio.run(resolve_profile('https://example.com/profile.json'))

    @staticmethod
    def test_success(tmp_path: Path) -> None:
        """A valid profile should be parsed and returned."""
        profile_data = {
            'version': '1',
            'name': 'Good',
            'manifests': ['https://example.com/a.json'],
        }

        async def fake_download(params: object) -> MagicMock:
            dest = params.destination  # type: ignore[attr-defined]
            dest.write_text(json.dumps(profile_data), encoding='utf-8')
            return MagicMock(success=True)

        with (
            patch('porringer.api.API.download', side_effect=fake_download),
            patch('tempfile.mkdtemp', return_value=str(tmp_path)),
        ):
            profile, temp_dir = asyncio.run(resolve_profile('https://example.com/profile.json'))
            assert profile.name == 'Good'
            assert profile.manifests == ['https://example.com/a.json']
            assert temp_dir == str(tmp_path)
