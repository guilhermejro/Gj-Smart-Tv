"""Download seguro (timeout, limite de tamanho, redirecionamentos validados) e parsing."""
import logging
import time
from typing import Callable, Optional
from urllib.parse import urljoin, urlsplit

import requests

from app.config import DOWNLOAD_DEADLINE, MAX_PLAYLIST_BYTES, MAX_REDIRECTS, REQUEST_TIMEOUT
from app.models.playlist import Playlist
from app.services.playlist_parser import parse_m3u
from app.utils.url import host_is_private, mask_url, validate_url

log = logging.getLogger(__name__)


class PlaylistError(Exception):
    """Erro com mensagem já apropriada para o usuário."""


def check_redirect(origin: str, target: str) -> str:
    """Valida um redirecionamento: sem rebaixar HTTPS para HTTP e sem sair da internet para a rede local."""
    target = validate_url(target)
    o, t = urlsplit(origin), urlsplit(target)
    if o.scheme == "https" and t.scheme != "https":
        raise PlaylistError("O servidor tentou redirecionar de HTTPS para HTTP (inseguro). Download bloqueado.")
    if not host_is_private(o.hostname) and host_is_private(t.hostname, resolve=True):
        raise PlaylistError("O servidor tentou redirecionar para um endereço da rede local. Download bloqueado.")
    return target


def download_text(url: str, progress: Optional[Callable[[int, int], None]] = None) -> str:
    current = validate_url(url)
    deadline = time.monotonic() + DOWNLOAD_DEADLINE
    session = requests.Session()
    session.headers["User-Agent"] = "GJ-Smart-TV/0.1"
    try:
        for _ in range(MAX_REDIRECTS + 1):
            resp = session.get(current, stream=True, timeout=REQUEST_TIMEOUT, allow_redirects=False)
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                current = check_redirect(current, urljoin(current, resp.headers.get("Location", "")))
                resp.close()
                continue
            break
        else:
            raise PlaylistError("Redirecionamentos demais ao acessar o endereço.")

        if resp.status_code in (401, 403):
            raise PlaylistError("O servidor recusou o acesso (verifique usuário, senha ou token do link).")
        if resp.status_code >= 400:
            raise PlaylistError(f"O servidor respondeu com erro HTTP {resp.status_code}.")

        total = int(resp.headers.get("Content-Length") or 0)
        if total > MAX_PLAYLIST_BYTES:
            raise PlaylistError("A playlist excede o tamanho máximo permitido (50 MB).")
        chunks, size = [], 0
        for chunk in resp.iter_content(65536):
            size += len(chunk)
            if size > MAX_PLAYLIST_BYTES:
                raise PlaylistError("A playlist excede o tamanho máximo permitido (50 MB).")
            chunks.append(chunk)
            if time.monotonic() > deadline:
                raise PlaylistError("O download demorou demais e foi cancelado.")
            if progress:
                progress(size, total)
        return b"".join(chunks).decode("utf-8", errors="replace")
    except PlaylistError:
        raise
    except ValueError as exc:
        raise PlaylistError(str(exc)) from exc
    except requests.exceptions.Timeout as exc:
        raise PlaylistError("Tempo esgotado ao acessar o endereço.") from exc
    except requests.exceptions.RequestException as exc:
        log.warning("Falha de rede em %s: %s", mask_url(current), type(exc).__name__)
        raise PlaylistError("Não foi possível acessar o endereço. Verifique sua conexão e o link.") from exc


def load_playlist(url: str, progress: Optional[Callable[[int, int], None]] = None) -> Playlist:
    text = download_text(url, progress)
    try:
        playlist = parse_m3u(text.splitlines())
    except ValueError as exc:
        raise PlaylistError(str(exc)) from exc
    if playlist.total == 0:
        raise PlaylistError("A playlist foi lida, mas não contém canais válidos.")
    log.info("Playlist carregada de %s: %d canais, %d ignorados", mask_url(url), playlist.total, playlist.skipped)
    return playlist
