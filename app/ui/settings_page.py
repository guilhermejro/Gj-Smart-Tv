"""Primeira execução e gerenciamento de fontes IPTV."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMessageBox, QProgressBar, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.services.settings_service import SettingsService
from app.utils.url import insecure_with_credentials, mask_url, validate_url
from app.utils.workers import PlaylistWorker


class SettingsPage(QWidget):
    changed = Signal()   # fontes alteradas -> recarregar playlist
    back = Signal()

    def __init__(self, settings: SettingsService):
        super().__init__()
        self.setObjectName("page")
        self.s = settings
        self._editing = None
        self._worker = None

        self.title = QLabel("Fontes IPTV")
        self.title.setObjectName("brand")
        self.intro = QLabel("Informe o link M3U/M3U8 da sua lista. Ele fica salvo apenas neste computador.")
        self.intro.setObjectName("muted")
        self.intro.setWordWrap(True)

        self.name = QLineEdit(placeholderText="Nome da fonte (ex.: Minha IPTV)")
        self.url = QLineEdit(placeholderText="https://servidor/playlist.m3u8")
        self.url.setEchoMode(QLineEdit.PasswordEchoOnEdit)  # oculta credenciais do link quando fora de edição
        self.url.returnPressed.connect(lambda: self._save(True))
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.hide()
        self.btn_save = QPushButton("Validar e salvar")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(lambda: self._save(True))
        self.btn_force = QPushButton("Salvar sem validar")
        self.btn_force.clicked.connect(lambda: self._save(False))
        self.btn_force.hide()
        self.btn_cancel = QPushButton("Cancelar edição")
        self.btn_cancel.clicked.connect(self._reset_form)
        self.btn_cancel.hide()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nome", "Endereço", "Ativa", "Padrão"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().hide()

        self.btns = []
        for text, fn in [("Usar como padrão", self._make_default), ("Ativar/Desativar", self._toggle),
                         ("Editar", self._edit), ("Excluir", self._delete)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            self.btns.append(b)
        self.btn_back = QPushButton("← Voltar")
        self.btn_back.clicked.connect(self.back)

        row = QHBoxLayout()
        for w in (self.btn_save, self.btn_force, self.btn_cancel):
            row.addWidget(w)
        row.addStretch()
        actions = QHBoxLayout()
        for b in self.btns:
            actions.addWidget(b)
        actions.addStretch()
        actions.addWidget(self.btn_back)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 30, 40, 30)
        lay.setSpacing(10)
        for w in (self.title, self.intro, self.name, self.url):
            lay.addWidget(w)
        lay.addLayout(row)
        lay.addWidget(self.bar)
        lay.addWidget(self.msg)
        lay.addWidget(self.table, 1)
        lay.addLayout(actions)
        self.refresh_table()

    # ---- modo ----
    def set_first_run(self, first: bool):
        self.table.setVisible(not first)
        self.btn_back.setVisible(not first)
        for b in self.btns:
            b.setVisible(not first)
        self.title.setText("Bem-vindo ao GJ Smart TV" if first else "Fontes IPTV")

    def refresh_table(self):
        sources = self.s.list_sources()
        self.table.setRowCount(len(sources))
        for i, src in enumerate(sources):
            vals = [src.name, mask_url(src.url), "Sim" if src.active else "Não", "★" if src.is_default else ""]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if j == 0:
                    item.setData(Qt.UserRole, src.id)
                self.table.setItem(i, j, item)

    def _selected_id(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is None:
            self._say("Selecione uma fonte na tabela.", error=True)
            return None
        return item.data(Qt.UserRole)

    def _say(self, text, error=False):
        self.msg.setObjectName("error" if error else "muted")
        self.msg.setStyleSheet("")  # reaplica o estilo por objectName
        self.msg.style().unpolish(self.msg)
        self.msg.style().polish(self.msg)
        self.msg.setText(text)

    # ---- salvar ----
    def _save(self, validate: bool):
        if self._worker and self._worker.isRunning():
            return
        try:
            url = validate_url(self.url.text())
        except ValueError as exc:
            self._say(str(exc), error=True)
            return
        self.btn_force.hide()
        if not validate:
            self._commit(url)
            return
        self._set_busy(True, "Validando o endereço…")
        self._worker = PlaylistWorker(url, self)
        self._worker.done.connect(lambda pl, u=url: self._on_valid(pl, u))
        self._worker.failed.connect(self._on_invalid)
        self._worker.start()

    def _on_valid(self, playlist, url):
        self._set_busy(False)
        self._commit(url, f"Fonte salva — {playlist.total} canais encontrados.")

    def _on_invalid(self, message):
        self._set_busy(False)
        self._say(f"{message}\nVocê pode corrigir o link ou salvá-lo assim mesmo.", error=True)
        self.btn_force.show()

    def _commit(self, url, message="Fonte salva."):
        try:
            if self._editing is not None:
                self.s.update_source(self._editing, self.name.text(), url)
            else:
                self.s.add_source(self.name.text(), url)
        except ValueError as exc:
            self._say(str(exc), error=True)
            return
        warn = ("\nAtenção: este endereço usa HTTP sem criptografia; usuário, senha ou token "
                "trafegam em texto puro. Prefira HTTPS se o seu provedor oferecer.") \
            if insecure_with_credentials(url) else ""
        self._reset_form()
        self.refresh_table()
        self._say(message + warn)
        self.changed.emit()

    def _set_busy(self, busy, text=""):
        self.bar.setVisible(busy)
        self.btn_save.setEnabled(not busy)
        if busy:
            self._say(text)

    def _reset_form(self):
        self._editing = None
        self.name.clear()
        self.url.clear()
        self.btn_cancel.hide()
        self.btn_force.hide()

    # ---- ações da tabela ----
    def _make_default(self):
        if (sid := self._selected_id()) is not None:
            self.s.set_default(sid)
            self.refresh_table()
            self.changed.emit()

    def _toggle(self):
        if (sid := self._selected_id()) is not None:
            src = self.s.get_source(sid)
            self.s.set_active(sid, not src.active)
            self.refresh_table()
            self.changed.emit()

    def _edit(self):
        if (sid := self._selected_id()) is not None:
            src = self.s.get_source(sid)
            self._editing = sid
            self.name.setText(src.name)
            self.url.setText(src.url)
            self.btn_cancel.show()
            self._say("Editando a fonte selecionada.")

    def _delete(self):
        if (sid := self._selected_id()) is None:
            return
        src = self.s.get_source(sid)
        if QMessageBox.question(self, "Excluir fonte", f"Excluir “{src.name}”?") == QMessageBox.Yes:
            self.s.delete_source(sid)
            self.refresh_table()
            self.changed.emit()
