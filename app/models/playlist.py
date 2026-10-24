from dataclasses import dataclass, field
from typing import Dict, List

from app.models.channel import Channel


@dataclass
class Source:
    id: int
    name: str
    url: str
    active: bool = True
    is_default: bool = False


@dataclass
class Playlist:
    channels: List[Channel] = field(default_factory=list)
    skipped: int = 0
    truncated: bool = False

    @property
    def total(self) -> int:
        return len(self.channels)

    def categories(self) -> Dict[str, List[Channel]]:
        """Categorias na ordem em que aparecem na playlist."""
        out: Dict[str, List[Channel]] = {}
        for ch in self.channels:
            out.setdefault(ch.group, []).append(ch)
        return out

    def search(self, text: str) -> List[Channel]:
        t = text.strip().casefold()
        return [c for c in self.channels if t in c.name.casefold()] if t else list(self.channels)
