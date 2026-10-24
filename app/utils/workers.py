import logging

from PySide6.QtCore import QThread, Signal

from app.services.playlist_service import PlaylistError, load_playlist

log = logging.getLogger(__name__)


class PlaylistWorker(QThread):
    """Baixa e interpreta a playlist fora da thread da interface."""

    progress = Signal(int, int)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            self.done.emit(load_playlist(self._url, lambda a, b: self.progress.emit(a, b)))
        except PlaylistError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # não registra a exceção completa: pode conter a URL
            log.error("Erro inesperado ao carregar playlist: %s", type(exc).__name__)
            self.failed.emit("Erro inesperado ao carregar a playlist.")
