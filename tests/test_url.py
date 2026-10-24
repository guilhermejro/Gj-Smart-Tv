import logging
from app.utils.url import mask_url, validate_url, MaskingFilter
import pytest


def test_mascara_credenciais():
    m = mask_url("http://user:pass@host.tv:8080/get.php?username=bob&password=123&type=m3u")
    assert "bob" not in m and "123" not in m and "pass@" not in m
    assert "host.tv:8080" in m and "type=m3u" in m


def test_mascara_segmento_token():
    assert "abc123def456" not in mask_url("http://h.tv/live/abc123def456/1.ts")


def test_validate():
    assert validate_url(" https://a.com/x.m3u ") == "https://a.com/x.m3u"
    for bad in ("", "javascript:alert(1)", "file:///x", "http://"):
        with pytest.raises(ValueError):
            validate_url(bad)


def test_log_filter():
    rec = logging.LogRecord("t", logging.INFO, "", 0, "falha em http://u:p@h.tv/x?token=SEGREDO", (), None)
    MaskingFilter().filter(rec)
    assert "SEGREDO" not in rec.msg and "u:p" not in rec.msg
