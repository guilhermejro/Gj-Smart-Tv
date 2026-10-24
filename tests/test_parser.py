from app.services.playlist_parser import parse_m3u
import pytest

SAMPLE = '''\ufeff#EXTM3U
#EXTINF:-1 tvg-id="a" tvg-logo="http://x/l.png" group-title="Notícias, Brasil",Canal Um
http://srv/1.m3u8
#EXTINF:-1 group-title="Filmes",Ação HD
http://srv/2.ts
lixo sem extinf
#EXTINF:-1,
http://srv/3
#EXTINF:-1,Canal Um
http://srv/1.m3u8
#EXTINF:-1,Sem URL válida
file:///etc/passwd
'''


def test_parse_basico():
    pl = parse_m3u(SAMPLE.splitlines())
    assert pl.total == 2
    assert pl.channels[0].group == "Notícias, Brasil"
    assert pl.channels[0].logo == "http://x/l.png"
    assert pl.channels[1].name == "Ação HD"
    assert pl.skipped >= 3  # lixo, vazio, file://


def test_categorias_preservam_ordem():
    cats = list(parse_m3u(SAMPLE.splitlines()).categories())
    assert cats == ["Notícias, Brasil", "Filmes"]


def test_busca_e_iniciais():
    pl = parse_m3u(SAMPLE.splitlines())
    assert [c.name for c in pl.search("ação")] == ["Ação HD"]
    assert pl.channels[0].initials == "CU"


def test_conteudo_invalido():
    with pytest.raises(ValueError):
        parse_m3u(["<html>nao e playlist</html>"])
