import pytest
from app.database import Database
from app.models.channel import Channel
from app.services.settings_service import SettingsService


@pytest.fixture
def svc(tmp_path):
    return SettingsService(Database(tmp_path / "t.db"))


def test_fonte_persiste_entre_aberturas(tmp_path):
    p = tmp_path / "t.db"
    SettingsService(Database(p)).add_source("Minha", "http://a.com/x.m3u")
    s2 = SettingsService(Database(p))
    assert s2.has_sources() and s2.default_source().name == "Minha"


def test_url_invalida(svc):
    with pytest.raises(ValueError):
        svc.add_source("x", "ftp://a.com/x.m3u")
    with pytest.raises(ValueError):
        svc.add_source("x", "http://")


def test_padrao_ativar_excluir(svc):
    a = svc.add_source("A", "http://a.com/a.m3u")
    b = svc.add_source("B", "http://b.com/b.m3u")
    assert a.is_default and not b.is_default
    svc.set_default(b.id)
    assert svc.default_source().id == b.id
    svc.delete_source(b.id)
    assert svc.default_source().id == a.id
    svc.set_active(a.id, False)
    assert svc.default_source() is None


def test_favoritos_historico(svc):
    ch = Channel("Canal", "http://s/1")
    assert svc.toggle_favorite(ch) is True and svc.is_favorite(ch)
    assert svc.toggle_favorite(ch) is False
    svc.add_history(ch); svc.add_history(Channel("Outro", "http://s/2")); svc.add_history(ch)
    assert [c.name for c in svc.history()] == ["Canal", "Outro"]
    svc.clear_history()
    assert svc.history() == []


def test_preferencias(svc):
    assert svc.get("volume", "80") == "80"
    svc.set("volume", 55)
    assert svc.get("volume") == "55"
