import logging

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QStackedWidget

from app.config import APP_NAME
from app.models.playlist import Playlist
from app.services.player_service import PlayerService
from app.services.settings_service import SettingsService
from app.ui.home_page import HomePage
from app.ui.player_page import PlayerPage
from app.ui.settings_page import SettingsPage
from app.utils.workers import PlaylistWorker

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService, player: PlayerService):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setMinimumSize(900, 560)
        self.s, self.player = settings, player
        self.playlist = Playlist()
        self._worker = None

        self.home = HomePage(settings)
        self.player_page = PlayerPage(settings, player)
        self.settings_page = SettingsPage(settings)
        self.stack = QStackedWidget()
        for p in (self.home, self.player_page, self.settings_page):
            self.stack.addWidget(p)
        self.setCentralWidget(self.stack)

        self.home.playRequested.connect(self.open_player)
        self.home.liveRequested.connect(self.open_live)
        self.home.refreshRequested.connect(self.refresh)
        self.home.sourcesRequested.connect(self.open_settings)
        self.player_page.backRequested.connect(self.go_home)
        self.player_page.fullscreenRequested.connect(self.toggle_fullscreen)
        self.settings_page.back.connect(self.go_home)
        self.settings_page.changed.connect(self._sources_changed)

        QApplication.instance().installEventFilter(self)
        if self.s.has_sources():
            self.go_home()
            self.refresh()
        else:
            self.open_settings(first_run=True)

    # ---- navegação ----
    def go_home(self):
        if self.player_page.isVisible():
            self.player_page.stop()
        if self.isFullScreen():
            self.toggle_fullscreen(force=False)
        self.home.refresh_personal()
        self.stack.setCurrentWidget(self.home)

    def open_settings(self, first_run: bool = False):
        self.settings_page.set_first_run(first_run is True)
        self.settings_page.refresh_table()
        self.stack.setCurrentWidget(self.settings_page)

    def open_player(self, channel):
        self.stack.setCurrentWidget(self.player_page)
        if self.s.get("fullscreen", "0") == "1" and not self.isFullScreen():
            self.toggle_fullscreen(force=True)
        self.player_page.play_channel(channel)

    def open_live(self):
        pool = self.s.history(1) or self.playlist.channels[:1] or self.s.favorites()[:1]
        if pool:
            self.open_player(pool[0])
        else:
            self.home.show_error("Nenhum canal disponível ainda. Atualize a playlist ou revise suas fontes.")

    def toggle_fullscreen(self, force=None):
        on = (not self.isFullScreen()) if force is None else force
        self.showFullScreen() if on else self.showNormal()
        self.player_page.set_fullscreen(on)
        if self.player_page.isVisible():
            self.s.set("fullscreen", int(on))

    def go_back(self):
        if self.isFullScreen():
            self.toggle_fullscreen(force=False)
        elif self.stack.currentWidget() is self.player_page:
            self.go_home()
        elif self.stack.currentWidget() is self.settings_page and self.s.has_sources():
            self.go_home()
        elif self.stack.currentWidget() is self.home:
            self.home.clear_search()

    def open_search(self):
        if self.stack.currentWidget() is self.player_page:
            self.player_page.focus_search()
        elif self.stack.currentWidget() is self.home:
            self.home.focus_search()

    # ---- playlist ----
    def _sources_changed(self):
        if self.s.has_sources() and self.s.default_source():
            self.refresh()
            if self.stack.currentWidget() is self.settings_page and self.settings_page.table.isVisible() is False:
                self.go_home()
        else:
            self.home.set_status("● Sem fonte ativa", "error")

    def refresh(self):
        src = self.s.default_source()
        if src is None:
            self.home.set_status("● Sem fonte ativa", "error")
            self.home.show_error("Nenhuma fonte ativa. Abra “Fontes” para cadastrar ou ativar uma.")
            return
        if self._worker and self._worker.isRunning():
            return
        self.home.show_error("")
        self.home.set_status("● Atualizando…", "busy")
        self.home.set_loading(True)
        self._worker = PlaylistWorker(src.url, self)
        self._worker.progress.connect(lambda d, t: self.home.set_loading(True, d, t))
        self._worker.done.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_loaded(self, playlist: Playlist):
        self.playlist = playlist  # a reprodução em andamento não é interrompida
        self.home.set_loading(False)
        self.home.set_playlist(playlist)
        self.player_page.set_playlist(playlist)
        extra = f" ({playlist.skipped} entradas ignoradas)" if playlist.skipped else ""
        if playlist.truncated:
            extra += " A lista excedeu o limite de canais e foi cortada."
        self.home.set_status(f"● Conectado · {playlist.total} canais", "ok")
        self.home.status.setToolTip(f"Playlist carregada{extra}.")
        if self.stack.currentWidget() is self.settings_page:
            self.go_home()

    def _on_failed(self, message: str):
        self.home.set_loading(False)
        self.home.set_status("● Sem conexão", "error")
        self.home.show_error(f"{message} Sua fonte continua salva; use “Atualizar” para tentar de novo.")
        if self.stack.currentWidget() is self.settings_page and self.s.has_sources():
            self.go_home()

    # ---- atalhos ----
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and self.isActiveWindow():
            if self.player_page.isVisible():
                self.player_page.poke()
            if self._handle_key(ev):
                return True
        return super().eventFilter(obj, ev)

    def _handle_key(self, ev) -> bool:
        key, mods = ev.key(), ev.modifiers()
        if mods & Qt.ControlModifier:
            if key == Qt.Key_F:
                self.open_search()
                return True
            if key == Qt.Key_R:
                self.refresh()
                return True
            return False
        if key == Qt.Key_Escape:
            self.go_back()
            return True
        if isinstance(QApplication.focusWidget(), QLineEdit):
            return False  # deixa o usuário digitar
        if self.stack.currentWidget() is self.player_page:
            if key == Qt.Key_Space:
                self.player_page.toggle_pause()
            elif key == Qt.Key_F:
                self.toggle_fullscreen()
            elif key == Qt.Key_M:
                self.player_page.toggle_mute()
            else:
                return False
            return True
        return False

    def closeEvent(self, e):
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        self.player.shutdown()
        super().closeEvent(e)
