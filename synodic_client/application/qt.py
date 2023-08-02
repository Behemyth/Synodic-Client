"""gui"""

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from synodic_client.client import Client


def qt_application() -> None:
    """Entrypoint"""

    client = Client()

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)

    with client.resource("icon.png") as icon_path:
        icon = QIcon(str(icon_path))

        tray = QSystemTrayIcon()
        tray.setIcon(icon)

    tray.setVisible(True)

    menu = QMenu()
    action = QAction("About")
    menu.addAction(action)

    quit_action = QAction("Quit")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    app.exec_()
