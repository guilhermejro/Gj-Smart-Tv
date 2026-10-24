import locale
import logging
import sys

from PySide6.QtGui import QIcon, QImageReader
from PySide6.QtWidgets import QApplication

from app.config import APP_ID, APP_NAME, IS_WINDOWS, db_path, resource_path, setup_logging
from app.database import Database
from app.services.player_service import PlayerService
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.style import QSS


def _harden_windows() -> None:
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW("")  # remove o diretório atual da busca de DLLs
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)  # ícone correto na barra de tarefas


def main() -> int:
    if IS_WINDOWS:
        _harden_windows()
    setup_logging()
    QImageReader.setAllocationLimit(64)  # limita memória ao decodificar logos (MB)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(QSS)
    icon = resource_path("icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    locale.setlocale(locale.LC_NUMERIC, "C")  # exigido pelo libmpv
    try:
        settings = SettingsService(Database(db_path()))
        window = MainWindow(settings, PlayerService())
    except Exception:
        logging.getLogger(__name__).exception("Falha ao iniciar")
        raise
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
