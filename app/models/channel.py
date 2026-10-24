import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    group: str = "Sem categoria"
    logo: str = ""
    tvg_id: str = ""
    tvg_name: str = ""

    @property
    def key(self) -> str:
        """Identificador estável sem expor a URL (que pode conter credenciais)."""
        return hashlib.sha256(f"{self.name}\n{self.url}".encode("utf-8")).hexdigest()

    @property
    def initials(self) -> str:
        words = [w for w in self.name.replace("-", " ").split() if w[:1].isalnum()]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return (words[0][0] + words[1][0]).upper()
