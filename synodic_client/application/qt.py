"""gui"""

from typing import LiteralString

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon

from synodic_client.client import Client

icon: LiteralString = 'icon.png'


class MainWindow(QMainWindow):
    """_summary_

    Args:
        QMainWindow: _description_
    """

    def __init__(self) -> None:
        super().__init__()


def application() -> None:
    """Entrypoint"""

    client = Client()

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)

    with client.resource(icon) as icon_path:
        qt_icon = QIcon(str(icon_path))

    tray = QSystemTrayIcon()
    tray.setIcon(qt_icon)

    tray.setVisible(True)

    window = MainWindow()
    window.setWindowTitle('Synodic Client')

    menu = QMenu()

    open_action = QAction('Open')
    menu.addAction(open_action)
    open_action.triggered.connect(window.show)

    settings_action = QAction('Settings')
    menu.addAction(settings_action)

    quit_action = QAction('Quit')
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    app.exec_()
