"""Parser M3U/M3U8 tolerante a erros. Nunca executa conteúdo da playlist."""
import re
from typing import Iterable, Optional, Tuple

from app import config

from app.models.channel import Channel
from app.models.playlist import Playlist

_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def _clean(text: str, limit: int) -> str:
    return _CTRL.sub("", text).strip()[:limit]


def parse_m3u(lines: Iterable[str]) -> Playlist:
    channels, seen = [], set()
    skipped = 0
    pending: Optional[Tuple[str, dict]] = None
    saw_header = False
    truncated = False

    for raw in lines:
        if len(raw) > config.MAX_LINE_LENGTH:
            skipped += 1
            pending = None
            continue
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("#EXTM3U"):
            saw_header = True
            continue
        if upper.startswith("#EXTINF"):
            pending = _parse_extinf(line)
            if pending is None:
                skipped += 1
            continue
        if line.startswith("#"):
            continue
        if pending is None:
            skipped += 1
            continue
        name, attrs = pending
        pending = None
        if not line.lower().startswith(config.STREAM_SCHEMES) or not name:
            skipped += 1
            continue
        key = (name.casefold(), line)
        if key in seen:
            continue
        if len(channels) >= config.MAX_CHANNELS:
            truncated = True
            break
        seen.add(key)
        logo = attrs.get("tvg-logo", "").strip()
        if len(logo) > config.MAX_LOGO_URL_LENGTH or not logo.lower().startswith(("http://", "https://")):
            logo = ""
        channels.append(
            Channel(
                name=name,
                url=line,
                group=_clean(attrs.get("group-title", ""), config.MAX_NAME_LENGTH) or "Sem categoria",
                logo=logo,
                tvg_id=_clean(attrs.get("tvg-id", ""), 100),
                tvg_name=_clean(attrs.get("tvg-name", ""), config.MAX_NAME_LENGTH),
            )
        )
    if not saw_header and not channels:
        raise ValueError("O conteúdo não parece uma playlist M3U (cabeçalho #EXTM3U ausente).")
    return Playlist(channels=channels, skipped=skipped, truncated=truncated)


def _parse_extinf(line: str):
    """#EXTINF:-1 tvg-id="x" group-title="Y",Nome — vírgulas entre aspas são respeitadas."""
    in_q, split_at = False, -1
    for i, ch in enumerate(line):
        if ch == '"':
            in_q = not in_q
        elif ch == "," and not in_q:
            split_at = i
            break
    head, title = (line[:split_at], line[split_at + 1:]) if split_at >= 0 else (line, "")
    attrs = dict(_ATTR_RE.findall(head))
    name = _clean(title, config.MAX_NAME_LENGTH) or _clean(attrs.get("tvg-name", ""), config.MAX_NAME_LENGTH)
    return name, attrs
