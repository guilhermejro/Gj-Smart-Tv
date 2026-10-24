import logging
import sqlite3

import pytest

from app import config
from app.database import Database
from app.models.channel import Channel
from app.services import playlist_service
from app.services.playlist_parser import parse_m3u
from app.services.playlist_service import PlaylistError, check_redirect
from app.services.settings_service import SettingsService
from app.utils import secrets
from app.utils.url import (MaskingFormatter, has_credentials, host_is_private,
                           insecure_with_credentials)


# ---- proteção em repouso ----
@pytest.fixture
def fake_windows(monkeypatch):
    """Simula DPAPI com uma transformação reversível, para testar a lógica fora do Windows."""
    monkeypatch.setattr(secrets, "IS_WINDOWS", True)
    monkeypatch.setattr(secrets, "_dpapi", lambda data, protect: bytes(b ^ 0x5A for b in data))


def test_protect_roundtrip(fake_windows):
    url = "http://u:p@h.tv/get.php?token=SEGREDO"
    stored = secrets.protect(url)
    assert stored.startswith(secrets.PREFIX) and "SEGREDO" not in stored and "h.tv" not in stored
    assert secrets.unprotect(stored) == url
    assert secrets.protect(stored) == stored          # idempotente
    assert secrets.unprotect("http://legado/x.m3u") == "http://legado/x.m3u"  # valor legado em texto puro


def test_linux_nao_le_dado_dpapi(monkeypatch):
    monkeypatch.setattr(secrets, "IS_WINDOWS", False)
    assert secrets.unprotect(secrets.PREFIX + "abc") == ""


def test_banco_nao_guarda_url_em_texto_puro(fake_windows, tmp_path):
    db = Database(tmp_path / "s.db")
    svc = SettingsService(db)
    svc.add_source("X", "http://u:p@h.tv/get.php?token=SEGREDO")
    ch = Channel("Canal", "http://srv/live/user/pass123/1.ts")
    svc.toggle_favorite(ch)
    svc.add_history(ch)
    raw = sqlite3.connect(tmp_path / "s.db")
    dump = " ".join(str(c) for t in ("sources", "favorites", "history") for r in raw.execute(f"select * from {t}") for c in r)
    assert "SEGREDO" not in dump and "pass123" not in dump and "h.tv" not in dump
    assert svc.default_source().url == "http://u:p@h.tv/get.php?token=SEGREDO"   # app continua lendo
    assert svc.favorites()[0].url == ch.url and svc.is_favorite(ch)


def test_migracao_de_banco_antigo(fake_windows, tmp_path):
    p = tmp_path / "old.db"
    db = Database(p)  # esquema antigo: URL em texto puro e chave "nome|url"
    db.execute("INSERT INTO sources(name,url,active,is_default) VALUES('A','http://a.com/x.m3u?token=T0K',1,1)")
    db.execute("INSERT INTO favorites VALUES('Canal|http://s/1.ts','Canal','http://s/1.ts','G','')")
    svc = SettingsService(db)
    assert svc.default_source().url == "http://a.com/x.m3u?token=T0K"
    assert svc.is_favorite(Channel("Canal", "http://s/1.ts"))
    raw = sqlite3.connect(p)
    assert "T0K" not in str(raw.execute("select url from sources").fetchall())
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 2


# ---- URLs ----
def test_credenciais_e_http():
    assert has_credentials("http://u:p@h.tv/x") and has_credentials("http://h.tv/x?password=1")
    assert not has_credentials("https://h.tv/lista.m3u")
    assert insecure_with_credentials("http://h.tv/x?token=1")
    assert not insecure_with_credentials("https://h.tv/x?token=1")


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "10.0.0.5", "192.168.1.9",
                                  "169.254.169.254", "::1", "meu.local", "0.0.0.0"])
def test_hosts_privados(host):
    assert host_is_private(host)


def test_hosts_publicos():
    assert not host_is_private("8.8.8.8") and not host_is_private("exemplo.com")


def test_redirecionamentos():
    assert check_redirect("https://a.com/x", "https://b.com/y") == "https://b.com/y"
    with pytest.raises(PlaylistError, match="HTTPS"):
        check_redirect("https://a.com/x", "http://b.com/y")
    with pytest.raises(PlaylistError, match="rede local"):
        check_redirect("http://8.8.8.8/x", "http://169.254.169.254/latest/meta-data")
    with pytest.raises(PlaylistError, match="rede local"):
        check_redirect("http://8.8.8.8/x", "http://127.0.0.1:8080/admin")
    assert check_redirect("http://192.168.0.2/x", "http://192.168.0.3/y")  # origem já é LAN: permitido


def test_formatter_mascara_traceback():
    fmt = MaskingFormatter("%(message)s")
    try:
        raise RuntimeError("falha http://u:p@h.tv/get.php?token=SEGREDO")
    except RuntimeError:
        import sys
        rec = logging.LogRecord("t", logging.ERROR, "", 0, "erro em http://h.tv/a?password=XYZ", (), sys.exc_info())
    out = fmt.format(rec)
    assert "SEGREDO" not in out and "XYZ" not in out and "u:p@" not in out


# ---- parser: limites ----
def test_limite_de_canais(monkeypatch):
    monkeypatch.setattr(config, "MAX_CHANNELS", 3)
    lines = ["#EXTM3U"] + [f"#EXTINF:-1,C{i}\nhttp://s/{i}" for i in range(10)]
    pl = parse_m3u("\n".join(lines).splitlines())
    assert pl.total == 3 and pl.truncated


def test_linhas_enormes_e_logo_invalido():
    big = "#EXTINF:-1,Nome\n" + "http://s/" + "a" * 5000
    ok = '#EXTINF:-1 tvg-logo="file:///etc/passwd" group-title="G\x00X",Bom\x07\nhttp://s/ok.ts'
    pl = parse_m3u(("#EXTM3U\n" + big + "\n" + ok).splitlines())
    assert pl.total == 1 and pl.channels[0].logo == "" and pl.channels[0].name == "Bom"
    assert pl.channels[0].group == "GX"


def test_esquema_proibido_no_stream():
    pl = parse_m3u(["#EXTM3U", "#EXTINF:-1,A", "file:///etc/passwd", "#EXTINF:-1,B", "javascript:alert(1)"])
    assert pl.total == 0 and pl.skipped == 2
