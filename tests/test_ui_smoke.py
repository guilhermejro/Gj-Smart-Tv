import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.database import Database  # noqa: E402
from app.models.playlist import Playlist  # noqa: E402
from app.services.player_service import PlayerService  # noqa: E402
from app.services.playlist_parser import parse_m3u  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

M3U = ['#EXTM3U'] + [f'#EXTINF:-1 group-title="G{i % 3}",Canal {i}\nhttp://s/{i}.m3u8' for i in range(30)]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_primeira_execucao_mostra_cadastro(qapp, tmp_path):
    win = MainWindow(SettingsService(Database(tmp_path / "a.db")), PlayerService())
    assert win.stack.currentWidget() is win.settings_page
    assert not win.settings_page.table.isVisibleTo(win.settings_page)


def test_home_categorias_busca_favoritos(qapp, tmp_path):
    s = SettingsService(Database(tmp_path / "b.db"))
    s.add_source("X", "http://127.0.0.1:9/x.m3u")
    win = MainWindow(s, PlayerService())
    pl = parse_m3u("\n".join(M3U).splitlines())
    win._on_loaded(pl)
    assert win.home.chips.count() == 4 and win.home.grid.count() == 30
    win.home.search.setText("Canal 1")
    win.home._apply_filter()
    assert win.home.grid.count() == 11
    ch = pl.channels[0]
    s.toggle_favorite(ch)
    win.home.refresh_personal()
    assert win.home.fav.count() == 1


def test_player_sem_libmpv_mostra_mensagem(qapp, tmp_path):
    s = SettingsService(Database(tmp_path / "c.db"))
    s.add_source("X", "http://127.0.0.1:9/x.m3u")
    win = MainWindow(s, PlayerService())
    pl = parse_m3u("\n".join(M3U).splitlines())
    win._on_loaded(pl)
    win.open_player(pl.channels[2])
    assert s.history()[0].name == "Canal 2"          # histórico gravado
    if not win.player.available:                      # sem libmpv: mensagem, sem encerrar
        assert "libmpv" in win.player_page.unavailable.text()
    win.player_page.step(1)
    assert win.player_page.current.name == "Canal 3"
