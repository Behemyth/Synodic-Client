"""App entrypoint"""

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def main() -> None:
    """Entrypoint"""
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)

    # Create the icon
    icon_path = Path("icon.png").absolute()

    assert icon_path.exists()

    icon = QIcon(str(icon_path))

    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setVisible(True)

    menu = QMenu()
    action = QAction("A menu item")
    menu.addAction(action)

    quit_action = QAction("Quit")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    app.exec_()


if __name__ == "__main__":
    main()
