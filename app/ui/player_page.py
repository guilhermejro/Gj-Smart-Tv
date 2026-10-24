from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QProgressBar, QPushButton, QSlider,
                               QStackedLayout, QVBoxLayout, QWidget)

from app.models.channel import Channel
from app.models.playlist import Playlist
from app.services.player_service import MpvUnavailable, PlayerService
from app.services.settings_service import SettingsService

ALL = "Todas as categorias"
HIDE_AFTER_MS = 3000


class PlayerPage(QWidget):
    backRequested = Signal()
    fullscreenRequested = Signal()

    def __init__(self, settings: SettingsService, player: PlayerService):
        super().__init__()
        self.setObjectName("page")
        self.s, self.player = settings, player
        self.playlist = Playlist()
        self.current = None
        self._visible = []
        self._fullscreen = False
        self._muted = False
        self._last_cursor, self._idle_ms = QCursor.pos(), 0

        # --- barra superior ---
        self.top = QWidget()
        back = QPushButton("← Início")
        back.clicked.connect(self.backRequested)
        self.title = QLabel("—")
        self.title.setObjectName("section")
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.btn_retry = QPushButton("Tentar novamente")
        self.btn_retry.clicked.connect(self.player.retry)
        self.btn_retry.hide()
        t = QHBoxLayout(self.top)
        t.setContentsMargins(0, 0, 0, 0)
        for w in (back, self.title):
            t.addWidget(w)
        t.addStretch()
        t.addWidget(self.status)
        t.addWidget(self.btn_retry)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setTextVisible(False)
        self.busy.setFixedHeight(4)
        self.busy.hide()

        # --- vídeo (janela nativa que recebe o mpv) ---
        self.video = QWidget()
        self.video.setAttribute(Qt.WA_NativeWindow)
        self.video.setStyleSheet("background:#000;")
        self.unavailable = QLabel("")
        self.unavailable.setAlignment(Qt.AlignCenter)
        self.unavailable.setWordWrap(True)
        self.unavailable.setObjectName("error")
        self.stack_host = QWidget()
        self.stack = QStackedLayout(self.stack_host)
        self.stack.addWidget(self.video)
        self.stack.addWidget(self.unavailable)

        # --- lista lateral ---
        self.side = QWidget()
        self.side.setFixedWidth(320)
        self.q = QLineEdit(placeholderText="Buscar na lista (Ctrl+F)")
        self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(self._fill_list)
        self.cat = QComboBox()
        self.cat.currentIndexChanged.connect(self._fill_list)
        self.list = QListWidget()
        self.list.setObjectName("side")
        self.list.itemActivated.connect(lambda it: self.play_channel(it.data(Qt.UserRole)))
        self.list.itemClicked.connect(lambda it: self.play_channel(it.data(Qt.UserRole)))
        sl = QVBoxLayout(self.side)
        sl.setContentsMargins(0, 0, 0, 0)
        for w in (self.q, self.cat):
            sl.addWidget(w)
        sl.addWidget(self.list, 1)

        # --- controles ---
        self.controls = QWidget()
        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("⏯")
        self.btn_next = QPushButton("⏭")
        self.btn_mute = QPushButton("🔊")
        self.btn_fav = QPushButton("☆")
        self.btn_full = QPushButton("⛶")
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setFixedWidth(140)
        self.vol.setValue(int(self.s.get("volume", "80")))
        self.btn_prev.clicked.connect(lambda: self.step(-1))
        self.btn_next.clicked.connect(lambda: self.step(1))
        self.btn_play.clicked.connect(self.player.toggle_pause)
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_fav.clicked.connect(self.toggle_favorite)
        self.btn_full.clicked.connect(self.fullscreenRequested)
        self.vol.valueChanged.connect(self._on_volume)
        c = QHBoxLayout(self.controls)
        c.setContentsMargins(0, 0, 0, 0)
        for w in (self.btn_prev, self.btn_play, self.btn_next):
            c.addWidget(w)
        c.addStretch()
        for w in (self.btn_fav, self.btn_mute, self.vol, self.btn_full):
            c.addWidget(w)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self.stack_host, 1)
        body.addWidget(self.side)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.addWidget(self.top)
        lay.addWidget(self.busy)
        lay.addLayout(body, 1)
        lay.addWidget(self.controls)

        self.player.state_changed.connect(self._on_state)
        self._poll = QTimer(self, interval=250)
        self._poll.timeout.connect(self._tick)

    # ---- dados ----
    def set_playlist(self, playlist: Playlist):
        self.playlist = playlist
        self.cat.blockSignals(True)
        self.cat.clear()
        self.cat.addItems([ALL] + list(playlist.categories()))
        self.cat.blockSignals(False)
        self._fill_list()

    def _fill_list(self, *_):
        text = self.q.text().strip().casefold()
        cat = self.cat.currentText()
        src = self.playlist.channels if cat in ("", ALL) else self.playlist.categories().get(cat, [])
        self._visible = [c for c in src if text in c.name.casefold()] if text else list(src)
        self.list.setUpdatesEnabled(False)
        self.list.clear()
        for ch in self._visible:
            it = QListWidgetItem(("★ " if self.s.is_favorite(ch) else "") + ch.name)
            it.setData(Qt.UserRole, ch)
            self.list.addItem(it)
        self.list.setUpdatesEnabled(True)
        self._select_current()

    def _select_current(self):
        if self.current in self._visible:
            self.list.setCurrentRow(self._visible.index(self.current))

    # ---- reprodução ----
    def ensure_player(self) -> bool:
        if self.player.available:
            return True
        try:
            self.player.attach(int(self.video.winId()))
            self.player.set_volume(self.vol.value())
            self.stack.setCurrentWidget(self.video)
            return True
        except MpvUnavailable as exc:
            self.unavailable.setText(str(exc))
            self.stack.setCurrentWidget(self.unavailable)
            self.status.setText("libmpv ausente")
            return False

    def play_channel(self, ch: Channel):
        self.current = ch
        self.title.setText(ch.name)
        self.s.add_history(ch)
        self._sync_fav()
        if self.current not in self._visible:
            self.cat.setCurrentText(ALL)
            self.q.clear()
            self._fill_list()
        self._select_current()
        if self.ensure_player():
            self.player.play(ch.url)

    def step(self, delta: int):
        if not self._visible:
            return
        i = self._visible.index(self.current) if self.current in self._visible else -1
        self.play_channel(self._visible[(i + delta) % len(self._visible)])

    def stop(self):
        self.player.stop()

    # ---- controles ----
    def _on_state(self, state: str, message: str):
        self.status.setText(message)
        self.busy.setVisible(state in ("loading", "retrying"))
        self.btn_retry.setVisible(state in ("failed", "retrying"))
        self.btn_play.setText("▶" if state == "paused" else "⏸" if state == "playing" else "⏯")

    def toggle_mute(self):
        self._muted = not self._muted
        self.player.set_mute(self._muted)
        self.btn_mute.setText("🔇" if self._muted else "🔊")

    def _on_volume(self, v: int):
        self.player.set_volume(v)
        self.s.set("volume", v)

    def toggle_favorite(self):
        if self.current:
            self.s.toggle_favorite(self.current)
            self._sync_fav()
            self._fill_list()

    def _sync_fav(self):
        self.btn_fav.setText("★" if self.current and self.s.is_favorite(self.current) else "☆")

    def toggle_pause(self):
        self.player.toggle_pause()

    def focus_search(self):
        self._reveal()
        self.q.setFocus()
        self.q.selectAll()

    # ---- tela cheia: controles discretos ----
    def set_fullscreen(self, on: bool):
        self._fullscreen = on
        self._idle_ms = 0
        self._reveal()

    def _reveal(self):
        for w in (self.top, self.controls, self.side):
            w.show()
        self._idle_ms = 0

    def poke(self):
        if self.isVisible():
            self._reveal()

    def _tick(self):
        pos = QCursor.pos()  # o mpv captura o mouse na janela nativa; por isso, consultamos o cursor
        if pos != self._last_cursor:
            self._last_cursor = pos
            if self._fullscreen:
                self._reveal()
            return
        if self._fullscreen and not self.q.hasFocus():
            self._idle_ms += self._poll.interval()
            if self._idle_ms >= HIDE_AFTER_MS:
                for w in (self.top, self.controls, self.side):
                    w.hide()

    def showEvent(self, e):
        self._poll.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._poll.stop()
        super().hideEvent(e)
