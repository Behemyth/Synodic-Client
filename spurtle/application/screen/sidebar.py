"""Manifest sidebar — a vertical panel for selecting cached project directories.

:class:`ManifestItem` renders a single directory as a row with an inline
close button visible on hover.  :class:`ManifestSidebar` manages a
scrollable column of items plus an *Add* button, emitting signals for
selection, removal, and addition.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from spurtle.application.screen.schema import PreviewPhase
from spurtle.application.theme import (
    SIDEBAR_ADD_STYLE,
    SIDEBAR_CLOSE_STYLE,
    SIDEBAR_HEADER_STYLE,
    SIDEBAR_ITEM_DIMMED_STYLE,
    SIDEBAR_ITEM_HEIGHT,
    SIDEBAR_ITEM_SELECTED_STYLE,
    SIDEBAR_ITEM_STYLE,
    SIDEBAR_LABEL_DIMMED_STYLE,
    SIDEBAR_LABEL_STYLE,
    SIDEBAR_PHASE_DONE_STYLE,
    SIDEBAR_PHASE_ERROR_STYLE,
    SIDEBAR_PHASE_INSTALLING_STYLE,
    SIDEBAR_PHASE_LOADING_STYLE,
    SIDEBAR_PHASE_READY_STYLE,
    SIDEBAR_SPACING,
    SIDEBAR_STYLE,
    SIDEBAR_WIDTH,
)

logger = logging.getLogger(__name__)

_PHASE_LABELS: dict[PreviewPhase, tuple[str, str]] = {
    PreviewPhase.LOADING: ('Loading…', SIDEBAR_PHASE_LOADING_STYLE),
    PreviewPhase.PREVIEWING: ('Checking…', SIDEBAR_PHASE_LOADING_STYLE),
    PreviewPhase.READY: ('Ready', SIDEBAR_PHASE_READY_STYLE),
    PreviewPhase.INSTALLING: ('Installing…', SIDEBAR_PHASE_INSTALLING_STYLE),
    PreviewPhase.DONE: ('Done', SIDEBAR_PHASE_DONE_STYLE),
    PreviewPhase.ERROR: ('Error', SIDEBAR_PHASE_ERROR_STYLE),
}


class ManifestItem(QFrame):
    """A sidebar row representing a single cached project directory.

    Emits :attr:`clicked` when the item body is pressed and
    :attr:`remove_requested` when the close button is pressed.
    """

    clicked = Signal(str)
    """Emitted with the item key when the item is clicked."""

    remove_requested = Signal(str)
    """Emitted with the item key when the × button is clicked."""

    def __init__(
        self,
        key: str,
        name: str = '',
        *,
        valid: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the item.

        Args:
            key: Unique identifier (resolved path string or URL).
            name: Optional human-readable name.
            valid: When ``False`` the item renders dimmed.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName('sidebarItem')
        self._key = key
        self._name = name
        self._valid = valid
        self._selected = False

        self.setFixedHeight(SIDEBAR_ITEM_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        display = name or key.rsplit('/', 1)[-1] or key
        self._label = QLabel(display)
        self._label.setStyleSheet(SIDEBAR_LABEL_STYLE if valid else SIDEBAR_LABEL_DIMMED_STYLE)
        self._label.setToolTip(key)
        layout.addWidget(self._label, stretch=1)

        # Phase indicator (updated externally)
        self._phase_label = QLabel()
        self._phase_label.hide()
        layout.addWidget(self._phase_label)

        self._close_btn = QPushButton('\u00d7')  # ×
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.setStyleSheet(SIDEBAR_CLOSE_STYLE)
        self._close_btn.setToolTip('Remove')
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._on_close)
        layout.addWidget(self._close_btn)

        self.setToolTip(key)

    # --- Properties -------------------------------------------------------

    @property
    def key(self) -> str:
        """Return the item key."""
        return self._key

    @property
    def selected(self) -> bool:
        """Return whether this item is currently selected."""
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        """Set the selected state and update styling."""
        self._selected = value
        self._apply_style()

    # --- Public API -------------------------------------------------------

    def set_phase(self, phase: PreviewPhase) -> None:
        """Update the phase indicator label."""
        info = _PHASE_LABELS.get(phase)
        if info is not None:
            text, style = info
            self._phase_label.setText(text)
            self._phase_label.setStyleSheet(style)
            self._phase_label.show()
        else:
            self._phase_label.hide()

    # --- Styling -----------------------------------------------------------

    def _apply_style(self) -> None:
        """Apply the appropriate stylesheet based on state."""
        if self._selected:
            self.setStyleSheet(SIDEBAR_ITEM_SELECTED_STYLE)
        elif not self._valid:
            self.setStyleSheet(SIDEBAR_ITEM_DIMMED_STYLE)
        else:
            self.setStyleSheet(SIDEBAR_ITEM_STYLE)

    # --- Events ------------------------------------------------------------

    def mousePressEvent(self, _event: object) -> None:
        """Emit :attr:`clicked` on mouse press."""
        self.clicked.emit(self._key)

    def _on_close(self) -> None:
        """Emit :attr:`remove_requested` when the × button is clicked."""
        self.remove_requested.emit(self._key)


class ManifestSidebar(QWidget):
    """Vertical sidebar for managing cached project directories.

    Displays a scrollable column of :class:`ManifestItem` widgets with
    a trailing *Add* button.  Emits signals for user interactions.
    """

    selection_changed = Signal(str)
    """Emitted with the item key when an item is clicked."""

    remove_requested = Signal(str)
    """Emitted with the item key when an item's close button is clicked."""

    add_requested = Signal()
    """Emitted when the Add (+) button is clicked."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the sidebar."""
        super().__init__(parent)
        self._items: list[ManifestItem] = []
        self._selected_key: str | None = None

        self.setFixedWidth(SIDEBAR_WIDTH)

        frame = QFrame(self)
        frame.setObjectName('sidebar')
        frame.setStyleSheet(SIDEBAR_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(frame)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(SIDEBAR_SPACING)

        # Header
        header = QLabel('PROJECTS')
        header.setStyleSheet(SIDEBAR_HEADER_STYLE)
        frame_layout.addWidget(header)

        # Scroll area for the items
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._container = QWidget()
        self._column = QVBoxLayout(self._container)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(SIDEBAR_SPACING)
        self._column.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._column.addStretch()

        self._scroll.setWidget(self._container)
        frame_layout.addWidget(self._scroll, stretch=1)

        # Add (+) button at the bottom
        self._add_btn = QPushButton('+  Add Project')
        self._add_btn.setStyleSheet(SIDEBAR_ADD_STYLE)
        self._add_btn.setToolTip('Add a manifest')
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self.add_requested.emit)
        frame_layout.addWidget(self._add_btn)

    # --- Public API --------------------------------------------------------

    @property
    def selected_key(self) -> str | None:
        """Return the currently selected item key."""
        return self._selected_key

    def set_directories(
        self,
        directories: list[tuple[str, str, bool]],
    ) -> None:
        """Rebuild all items from a list of ``(key, name, valid)`` tuples.

        Any previous selection is **not** restored — callers should call
        :meth:`select` afterwards if desired.
        """
        # Remove existing items
        for item in self._items:
            self._column.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        self._selected_key = None

        # Insert new items before the trailing stretch
        for insert_idx, (key, name, valid) in enumerate(directories):
            item = ManifestItem(key, name, valid=valid, parent=self._container)
            item.clicked.connect(self._on_item_clicked)
            item.remove_requested.connect(self._on_item_remove)
            self._column.insertWidget(insert_idx, item)
            self._items.append(item)

    def select(self, key: str | None) -> None:
        """Programmatically select an item by key.

        If *key* is ``None`` or not found, the first item (if any) is
        selected instead.
        """
        target: str | None = None
        if key is not None:
            for item in self._items:
                if item.key == key:
                    target = key
                    break

        if target is None and self._items:
            target = self._items[0].key

        self._selected_key = target
        for item in self._items:
            item.selected = item.key == target

        if target is not None:
            self.selection_changed.emit(target)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the add button and all items."""
        self._add_btn.setEnabled(enabled)
        for item in self._items:
            item.setEnabled(enabled)

    def get_item(self, key: str) -> ManifestItem | None:
        """Return the :class:`ManifestItem` for *key*, or ``None``."""
        for item in self._items:
            if item.key == key:
                return item
        return None

    # --- Internal slots ----------------------------------------------------

    def _on_item_clicked(self, key: str) -> None:
        """Handle an item click — update selection and emit signal."""
        self._selected_key = key
        for item in self._items:
            item.selected = item.key == key
        self.selection_changed.emit(key)

    def _on_item_remove(self, key: str) -> None:
        """Forward the remove request signal."""
        self.remove_requested.emit(key)
