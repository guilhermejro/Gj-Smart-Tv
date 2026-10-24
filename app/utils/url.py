"""Validação de URLs e mascaramento de credenciais."""
import ipaddress
import logging
import re
import socket
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.config import ALLOWED_SCHEMES

_SENSITIVE = re.compile(r"(token|key|pass|pwd|secret|auth|user|sig)", re.I)
_URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.I)
_SEGMENT_RE = re.compile(r"[A-Za-z0-9_-]{6,}")


def validate_url(url: str) -> str:
    """Retorna a URL limpa ou levanta ValueError."""
    url = (url or "").strip()
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("Use um endereço http:// ou https://.")
    if not parts.netloc or not parts.hostname:
        raise ValueError("O endereço não possui um servidor válido.")
    return url


def _mask_segment(seg: str) -> str:
    if seg.lower().endswith((".m3u", ".m3u8", ".ts")):
        return seg
    if _SEGMENT_RE.fullmatch(seg) and any(c.isdigit() for c in seg):
        return "***"
    return seg


def mask_url(url: str) -> str:
    """Oculta usuário/senha, parâmetros sensíveis e segmentos que parecem credenciais."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
    except ValueError:
        return "***"
    if parts.username or parts.password:
        host = "***@" + host
    query = urlencode(
        [(k, "***" if _SENSITIVE.search(k) else v) for k, v in parse_qsl(parts.query)],
        safe="*",
    )
    path = "/".join(_mask_segment(s) for s in parts.path.split("/"))
    return urlunsplit((parts.scheme, host, path, query, ""))


class MaskingFilter(logging.Filter):
    """Mascara qualquer URL que apareça em mensagens de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _URL_RE.sub(lambda m: mask_url(m.group(0)), record.getMessage())
        record.args = ()
        return True


class MaskingFormatter(logging.Formatter):
    """Mascara URLs em toda a saída do log, inclusive tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        return _URL_RE.sub(lambda m: mask_url(m.group(0)), super().format(record))


def has_credentials(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.username or parts.password:
        return True
    return any(_SENSITIVE.search(k) for k, _ in parse_qsl(parts.query)) or \
        any(_SEGMENT_RE.fullmatch(s) and any(c.isdigit() for c in s) for s in parts.path.split("/"))


def insecure_with_credentials(url: str) -> bool:
    """HTTP puro com usuário/senha/token: o segredo trafega sem criptografia."""
    return urlsplit(url).scheme.lower() == "http" and has_credentials(url)


def _ip_is_private(ip) -> bool:
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_reserved or ip.is_unspecified)


def host_is_private(host: str, resolve: bool = False) -> bool:
    """True para localhost, IPs privados/loopback/link-local (incl. metadados de nuvem)."""
    host = (host or "").strip("[]").lower()
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return True
    try:
        return _ip_is_private(ipaddress.ip_address(host))
    except ValueError:
        pass
    if not resolve:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    return any(_ip_is_private(ipaddress.ip_address(i[4][0].split("%")[0])) for i in infos)
