"""Tests for the ManifestSidebar and ManifestItem widgets."""

from __future__ import annotations

from pathlib import Path

import pytest

from spurtle.application.screen.schema import PreviewPhase
from spurtle.application.screen.sidebar import ManifestItem, ManifestSidebar
from spurtle.application.theme import SIDEBAR_WIDTH

_EXPECTED_DIRECTORY_COUNT = 2


# ---------------------------------------------------------------------------
# ManifestItem
# ---------------------------------------------------------------------------


class TestManifestItemInit:
    """Basic construction and property access."""

    @staticmethod
    def test_key_property(tmp_path: object) -> None:
        """Verify the key property returns the construction key."""
        item = ManifestItem('/some/path', 'proj')
        assert item.key == '/some/path'

    @staticmethod
    def test_default_not_selected() -> None:
        """Verify a new item is not selected by default."""
        item = ManifestItem('/some/path', 'proj')
        assert item.selected is False

    @staticmethod
    def test_display_name_uses_explicit_name() -> None:
        """Verify label uses the explicit display name when provided."""
        item = ManifestItem('/some/path', 'My Project')
        assert item._label.text() == 'My Project'

    @staticmethod
    def test_display_name_falls_back_to_key_basename() -> None:
        """Verify label falls back to the last path/URL segment when no name is given."""
        item = ManifestItem('/some/path/mydir')
        assert item._label.text() == 'mydir'

    @staticmethod
    def test_tooltip_shows_full_key() -> None:
        """Verify the tooltip shows the full key string."""
        item = ManifestItem('/some/path', 'proj')
        assert item.toolTip() == '/some/path'


class TestManifestItemSelection:
    """Selection state changes."""

    @staticmethod
    def test_set_selected_true() -> None:
        """Verify setting selected to True updates the state."""
        item = ManifestItem('/some/path', 'proj')
        item.selected = True
        assert item.selected is True

    @staticmethod
    def test_set_selected_false() -> None:
        """Verify toggling selected back to False works."""
        item = ManifestItem('/some/path', 'proj')
        item.selected = True
        item.selected = False
        assert item.selected is False


class TestManifestItemPhase:
    """Phase indicator updates."""

    @staticmethod
    @pytest.mark.parametrize(
        ('phase', 'expected_text'),
        [
            (PreviewPhase.LOADING, 'Loading\u2026'),
            (PreviewPhase.READY, 'Ready'),
            (PreviewPhase.ERROR, 'Error'),
            (PreviewPhase.INSTALLING, 'Installing\u2026'),
            (PreviewPhase.DONE, 'Done'),
        ],
        ids=['loading', 'ready', 'error', 'installing', 'done'],
    )
    def test_phase_label(tmp_path: object, phase: PreviewPhase, expected_text: str) -> None:
        """Verify phase label text matches the phase enum."""
        item = ManifestItem('/some/path', 'proj')
        item.set_phase(phase)
        assert not item._phase_label.isHidden()
        assert item._phase_label.text() == expected_text


class TestManifestItemSignals:
    """Signal emission."""

    @staticmethod
    def test_clicked_on_mouse_press() -> None:
        """Verify clicked signal fires on mousePressEvent."""
        item = ManifestItem('/some/path', 'proj')
        received: list[str] = []
        item.clicked.connect(received.append)
        item.mousePressEvent(None)
        assert received == ['/some/path']

    @staticmethod
    def test_remove_requested_on_close() -> None:
        """Verify remove_requested signal fires on close button click."""
        item = ManifestItem('/some/path', 'proj')
        received: list[str] = []
        item.remove_requested.connect(received.append)
        item._close_btn.click()
        assert received == ['/some/path']


# ---------------------------------------------------------------------------
# ManifestSidebar
# ---------------------------------------------------------------------------


class TestManifestSidebarInit:
    """Basic construction."""

    @staticmethod
    def test_default_no_items() -> None:
        """Verify a new sidebar has no selection."""
        sidebar = ManifestSidebar()
        assert sidebar.selected_key is None

    @staticmethod
    def test_fixed_width() -> None:
        """Verify the sidebar minimum width matches the theme constant."""
        sidebar = ManifestSidebar()
        assert sidebar.minimumWidth() == SIDEBAR_WIDTH


class TestManifestSidebarSetDirectories:
    """Populating the sidebar with items."""

    @staticmethod
    def test_creates_items(tmp_path: object) -> None:
        """Verify set_directories creates the expected number of items."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True), ('/b', 'B', True)])
        assert len(sidebar._items) == _EXPECTED_DIRECTORY_COUNT

    @staticmethod
    def test_replaces_previous_items() -> None:
        """Verify set_directories replaces prior items completely."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True), ('/b', 'B', True)])
        sidebar.set_directories([('/c', 'C', True)])
        assert len(sidebar._items) == 1
        assert sidebar._items[0].key == '/c'

    @staticmethod
    def test_clears_selection() -> None:
        """Verify set_directories resets the selection to None."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True)])
        sidebar.select('/a')
        sidebar.set_directories([('/a', 'A', True)])
        assert sidebar.selected_key is None


class TestManifestSidebarSelect:
    """Selection behaviour."""

    @staticmethod
    def test_select_by_key() -> None:
        """Verify selecting a key updates selected_key."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True), ('/b', 'B', True)])
        sidebar.select('/b')
        assert sidebar.selected_key == '/b'

    @staticmethod
    def test_select_none_falls_back_to_first() -> None:
        """Verify selecting None falls back to the first item."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True), ('/b', 'B', True)])
        sidebar.select(None)
        assert sidebar.selected_key == '/a'

    @staticmethod
    def test_select_missing_key_falls_back_to_first() -> None:
        """Verify selecting a nonexistent key falls back to the first item."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True)])
        sidebar.select('/nonexistent')
        assert sidebar.selected_key == '/a'

    @staticmethod
    def test_select_emits_signal() -> None:
        """Verify select emits selection_changed with the selected key."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True)])
        received: list[str] = []
        sidebar.selection_changed.connect(received.append)
        sidebar.select('/a')
        assert received == ['/a']


class TestManifestSidebarGetItem:
    """Finding items by key."""

    @staticmethod
    def test_found() -> None:
        """Verify get_item returns the item matching the given key."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([('/a', 'A', True)])
        item = sidebar.get_item('/a')
        assert item is not None
        assert item.key == '/a'

    @staticmethod
    def test_not_found() -> None:
        """Verify get_item returns None for an unknown key."""
        sidebar = ManifestSidebar()
        sidebar.set_directories([])
        assert sidebar.get_item('/x') is None


class TestManifestSidebarSignals:
    """Signal forwarding from child items and the Add button."""

    @staticmethod
    def test_add_requested() -> None:
        """Verify add_requested fires when the add button is clicked."""
        sidebar = ManifestSidebar()
        received: list[bool] = []
        sidebar.add_requested.connect(lambda: received.append(True))
        sidebar._add_btn.click()
        assert received == [True]

    @staticmethod
    def test_remove_requested_forwarded(tmp_path: Path) -> None:
        """Verify remove_requested is forwarded from child items."""
        sidebar = ManifestSidebar()
        d1 = str(tmp_path / 'a')
        sidebar.set_directories([(d1, 'A', True)])
        received: list[str] = []
        sidebar.remove_requested.connect(received.append)
        # Simulate the item's close button click
        sidebar._items[0]._close_btn.click()
        assert received == [d1]

    @staticmethod
    def test_selection_changed_on_item_click(tmp_path: Path) -> None:
        """Verify selection_changed fires when an item is clicked."""
        sidebar = ManifestSidebar()
        d1 = str(tmp_path / 'a')
        d2 = str(tmp_path / 'b')
        sidebar.set_directories([(d1, 'A', True), (d2, 'B', True)])
        received: list[str] = []
        sidebar.selection_changed.connect(received.append)
        sidebar._items[1].mousePressEvent(None)
        assert received == [d2]


class TestManifestSidebarSetEnabled:
    """Enabling and disabling the sidebar."""

    @staticmethod
    def test_disable_add_button() -> None:
        """Verify disabling the sidebar disables the add button."""
        sidebar = ManifestSidebar()
        sidebar.set_enabled(False)
        assert not sidebar._add_btn.isEnabled()

    @staticmethod
    def test_reenable() -> None:
        """Verify re-enabling the sidebar re-enables the add button."""
        sidebar = ManifestSidebar()
        sidebar.set_enabled(False)
        sidebar.set_enabled(True)
        assert sidebar._add_btn.isEnabled()
