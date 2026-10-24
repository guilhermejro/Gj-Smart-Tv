"""Configuração global, caminhos locais (Linux e Windows) e limites de segurança."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "GJ Smart TV"
APP_SLUG = "gj-smart-tv"
APP_ID = "GJ.SmartTV.Desktop.1"  # AppUserModelID (Windows)
IS_WINDOWS = sys.platform == "win32"

ALLOWED_SCHEMES = ("http", "https")
STREAM_SCHEMES = ("http://", "https://", "rtmp://", "rtmps://", "rtsp://", "rtsps://", "udp://", "rtp://")

# --- limites (defesa contra playlists maliciosas ou gigantes) ---
MAX_PLAYLIST_BYTES = 50 * 1024 * 1024  # 50 MB já descompactados
DOWNLOAD_DEADLINE = 90                  # segundos para o download inteiro
REQUEST_TIMEOUT = (8, 20)               # (conexão, leitura)
MAX_REDIRECTS = 5
MAX_CHANNELS = 300_000
MAX_LINE_LENGTH = 4096
MAX_NAME_LENGTH = 200
MAX_LOGO_URL_LENGTH = 2048

MAX_RECONNECT_ATTEMPTS = 4
RECONNECT_DELAYS = (1, 2, 4, 8)
HISTORY_LIMIT = 30


def app_dir() -> Path:
    """Pasta do aplicativo (executável congelado ou raiz do projeto)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path:
    return app_dir() / "app" / "resources" / name


def data_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(base) / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    restrict_permissions(path, directory=True)
    return path


def restrict_permissions(path: Path, directory: bool = False) -> None:
    """Somente o dono lê/escreve (POSIX). No Windows, %LOCALAPPDATA% já é restrito ao usuário."""
    if IS_WINDOWS:
        return
    try:
        os.chmod(path, 0o700 if directory else 0o600)
    except OSError:
        pass


def db_path() -> Path:
    override = os.environ.get("GJTV_DB")
    return Path(override) if override else data_dir() / "gjtv.db"


def setup_logging() -> None:
    from app.utils.url import MaskingFormatter

    log_file = data_dir() / "gjtv.log"
    handler = RotatingFileHandler(log_file, maxBytes=512_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(MaskingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    restrict_permissions(log_file)
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # evita URLs completas em logs de debug
