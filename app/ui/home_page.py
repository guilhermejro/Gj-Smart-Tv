from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QProgressBar, QPushButton, QVBoxLayout, QWidget)

from app.models.playlist import Playlist
from app.services.settings_service import SettingsService
from app.ui.widgets.channel_list import ChannelList

ALL = "Todos"


class HomePage(QWidget):
    playRequested = Signal(object)
    liveRequested = Signal()
    refreshRequested = Signal()
    sourcesRequested = Signal()

    def __init__(self, settings: SettingsService):
        super().__init__()
        self.setObjectName("page")
        self.s = settings
        self.playlist = Playlist()
        self._shown = []

        brand = QLabel("GJ Smart TV")
        brand.setObjectName("brand")
        self.btn_live = QPushButton("▶  TV ao vivo")
        self.btn_live.setObjectName("primary")
        self.btn_live.clicked.connect(self.liveRequested)
        self.search = QLineEdit(placeholderText="Buscar canal (Ctrl+F)")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(220)
        self._debounce = QTimer(self, singleShot=True, interval=250)
        self._debounce.timeout.connect(self._apply_filter)
        self.search.textChanged.connect(lambda _t: self._debounce.start())
        btn_refresh = QPushButton("⟳  Atualizar")
        btn_refresh.clicked.connect(self.refreshRequested)
        btn_sources = QPushButton("⚙  Fontes")
        btn_sources.clicked.connect(self.sourcesRequested)
        self.status = QLabel("● Sem fonte")
        self.status.setObjectName("muted")

        head = QHBoxLayout()
        for w in (brand, self.btn_live):
            head.addWidget(w)
        head.addStretch()
        for w in (self.search, btn_refresh, btn_sources, self.status):
            head.addWidget(w)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        self.bar.hide()
        self.banner = QLabel("")
        self.banner.setObjectName("error")
        self.banner.setWordWrap(True)
        self.banner.hide()

        self.lbl_fav = QLabel("Favoritos")
        self.lbl_fav.setObjectName("section")
        self.fav = ChannelList(horizontal=True)
        self.lbl_rec = QLabel("Acessados recentemente")
        self.lbl_rec.setObjectName("section")
        self.rec = ChannelList(horizontal=True)
        clear = QPushButton("Limpar histórico")
        clear.clicked.connect(self._clear_history)
        rec_head = QHBoxLayout()
        rec_head.addWidget(self.lbl_rec)
        rec_head.addStretch()
        rec_head.addWidget(clear)

        self.lbl_cat = QLabel("Canais")
        self.lbl_cat.setObjectName("section")
        self.chips = QListWidget()
        self.chips.setObjectName("chips")
        self.chips.setFlow(QListWidget.LeftToRight)
        self.chips.setWrapping(False)
        self.chips.setFixedHeight(48)
        self.chips.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        self.chips.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chips.currentRowChanged.connect(lambda _r: self._apply_filter())
        self.grid = ChannelList()

        for lst in (self.fav, self.rec, self.grid):
            lst.channelActivated.connect(self.playRequested)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 16)
        lay.setSpacing(6)
        lay.addLayout(head)
        lay.addWidget(self.bar)
        lay.addWidget(self.banner)
        lay.addWidget(self.lbl_fav)
        lay.addWidget(self.fav)
        lay.addLayout(rec_head)
        lay.addWidget(self.rec)
        lay.addWidget(self.lbl_cat)
        lay.addWidget(self.chips)
        lay.addWidget(self.grid, 1)
        self.refresh_personal()

    # ---- estado ----
    def set_status(self, text: str, kind: str = "muted"):
        color = {"ok": "#3DDC97", "error": "#FF6B81", "busy": "#F5B942"}.get(kind, "#8A90A6")
        self.status.setStyleSheet(f"color:{color};")
        self.status.setText(text)

    def set_loading(self, loading: bool, done: int = 0, total: int = 0):
        self.bar.setVisible(loading)
        if loading:
            self.bar.setRange(0, total or 0)
            self.bar.setValue(done if total else 0)

    def show_error(self, text: str = ""):
        self.banner.setText(text)
        self.banner.setVisible(bool(text))

    # ---- conteúdo ----
    def refresh_personal(self):
        favs, hist = self.s.favorites(), self.s.history()
        self.fav.set_channels(favs)
        self.rec.set_channels(hist)
        for w in (self.lbl_fav, self.fav):
            w.setVisible(bool(favs))
        for w in (self.lbl_rec, self.rec):
            w.setVisible(bool(hist))

    def set_playlist(self, playlist: Playlist):
        self.playlist = playlist
        last = self.s.get("last_category", ALL)
        self.chips.blockSignals(True)
        self.chips.clear()
        names = [ALL] + list(playlist.categories())
        for n in names:
            self.chips.addItem(QListWidgetItem(n))
        self.chips.setCurrentRow(names.index(last) if last in names else 0)
        self.chips.blockSignals(False)
        self._apply_filter()

    def _apply_filter(self):
        text = self.search.text().strip()
        item = self.chips.currentItem()
        cat = item.text() if item else ALL
        if text:
            self._shown = self.playlist.search(text)
            self.lbl_cat.setText(f"Resultados da busca ({len(self._shown)})")
        elif cat == ALL:
            self._shown = self.playlist.channels
            self.lbl_cat.setText(f"Canais ({len(self._shown)})")
        else:
            self._shown = self.playlist.categories().get(cat, [])
            self.lbl_cat.setText(f"{cat} ({len(self._shown)})")
            self.s.set("last_category", cat)
        if cat == ALL:
            self.s.set("last_category", ALL)
        self.grid.set_channels(self._shown)

    def _clear_history(self):
        self.s.clear_history()
        self.refresh_personal()

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    def clear_search(self) -> bool:
        if self.search.text():
            self.search.clear()
            return True
        return False
