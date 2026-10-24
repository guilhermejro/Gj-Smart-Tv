"""Reprodução via libmpv (python-mpv), com reconexão limitada e erros claros."""
import locale
import logging
import os
import sys

from PySide6.QtCore import QObject, QTimer, Signal

from app.config import IS_WINDOWS, MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAYS, app_dir
from app.utils.url import mask_url

log = logging.getLogger(__name__)

INSTALL_HINT = (
    "A biblioteca libmpv não foi encontrada.\n"
    "Windows: execute windows\\fetch_libmpv.ps1 (ela baixa e verifica o libmpv-2.dll).\n"
    "Linux:  sudo apt install libmpv2   (em versões antigas: libmpv1)\n"
    "Depois reinicie o GJ Smart TV."
)


def _prepare_windows_dll_path() -> None:
    """Só procura a libmpv na pasta do próprio app (evita DLL hijacking pelo diretório atual)."""
    if not IS_WINDOWS:
        return
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for d in (app_dir(), app_dir() / "libs", exe_dir, os.path.join(exe_dir, "libs")):
        d = str(d)
        if os.path.isfile(os.path.join(d, "libmpv-2.dll")) or os.path.isfile(os.path.join(d, "mpv-2.dll")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            return


class MpvUnavailable(RuntimeError):
    pass


def load_mpv_module():
    """Importa python-mpv sem derrubar o app quando a libmpv não existe."""
    try:
        locale.setlocale(locale.LC_NUMERIC, "C")  # exigido pelo libmpv
        _prepare_windows_dll_path()
        import mpv  # noqa: WPS433 (import tardio proposital)
        return mpv
    except (OSError, ImportError) as exc:
        log.error("libmpv indisponível: %s", exc)
        raise MpvUnavailable(INSTALL_HINT) from exc


def _is_error_end(event) -> bool:
    try:
        data = event.as_dict() if hasattr(event, "as_dict") else dict(event["event"])
        reason = data.get("reason", b"")
        return str(reason).lower().strip("b'\"") == "error" or reason == 4
    except Exception:  # formato inesperado: não presume erro
        return False


class PlayerService(QObject):
    """Estados: idle, loading, playing, paused, retrying, failed."""

    state_changed = Signal(str, str)  # estado, mensagem
    _error = Signal(str)
    _core_idle = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mpv = None
        self._url = None
        self._attempt = 0
        self._paused = False
        self._timer = QTimer(self, singleShot=True)
        self._timer.timeout.connect(self._reconnect)
        self._error.connect(self._on_error)
        self._core_idle.connect(self._on_core_idle)

    @property
    def available(self) -> bool:
        return self._mpv is not None

    def attach(self, wid: int) -> None:
        """Cria o mpv dentro da janela nativa indicada. Levanta MpvUnavailable."""
        if self._mpv is not None:
            return
        mpv = load_mpv_module()
        try:
            self._mpv = mpv.MPV(
                wid=str(int(wid)), vo="gpu", hwdec="auto-safe", osc=False,
                input_default_bindings=False, input_vo_keyboard=False, ytdl=False,
                config=False, load_scripts=False,  # ignora mpv.conf e scripts de terceiros
                cache="yes", demuxer_max_bytes="32MiB", demuxer_max_back_bytes="8MiB",
                network_timeout=15,
            )
        except Exception as exc:
            raise MpvUnavailable(f"Não foi possível iniciar o mpv: {exc}") from exc

        @self._mpv.event_callback("end-file")
        def _end(event):
            if _is_error_end(event):
                self._error.emit("A transmissão falhou ou o formato não é suportado.")

        @self._mpv.property_observer("core-idle")
        def _idle(_name, value):
            if value is not None:
                self._core_idle.emit(bool(value))

    # ---- controle ----
    def play(self, url: str) -> None:
        self._url, self._attempt = url, 0
        self._timer.stop()
        self._start()

    def _start(self) -> None:
        if not self._mpv:
            return
        self._paused = False
        self.state_changed.emit("loading", "Carregando…")
        log.info("Reproduzindo %s", mask_url(self._url))
        try:
            self._mpv.pause = False
            self._mpv.play(self._url)
        except Exception as exc:
            self._error.emit(f"Erro ao iniciar a reprodução: {exc}")

    def retry(self) -> None:
        if self._url:
            self._attempt = 0
            self._timer.stop()
            self._start()

    def toggle_pause(self) -> None:
        if self._mpv and self._url:
            self._paused = not self._paused
            self._mpv.pause = self._paused
            self.state_changed.emit("paused" if self._paused else "playing", "Pausado" if self._paused else "")

    def set_volume(self, value: int) -> None:
        if self._mpv:
            self._mpv.volume = max(0, min(100, int(value)))

    def set_mute(self, muted: bool) -> None:
        if self._mpv:
            self._mpv.mute = bool(muted)

    def stop(self) -> None:
        self._timer.stop()
        self._url = None
        if self._mpv:
            try:
                self._mpv.command("stop")
            except Exception:
                pass
        self.state_changed.emit("idle", "")

    def shutdown(self) -> None:
        self._timer.stop()
        if self._mpv:
            try:
                self._mpv.terminate()
            except Exception:
                pass
            self._mpv = None

    # ---- eventos (sempre na thread da interface) ----
    def _on_core_idle(self, idle: bool) -> None:
        if not idle and self._url and not self._paused:
            self._attempt = 0
            self.state_changed.emit("playing", "")

    def _on_error(self, message: str) -> None:
        if not self._url:
            return
        if self._attempt >= MAX_RECONNECT_ATTEMPTS:
            self.state_changed.emit("failed", f"{message} Use “Tentar novamente”.")
            return
        delay = RECONNECT_DELAYS[min(self._attempt, len(RECONNECT_DELAYS) - 1)]
        self._attempt += 1
        self.state_changed.emit(
            "retrying", f"Falha na transmissão. Reconectando ({self._attempt}/{MAX_RECONNECT_ATTEMPTS}) em {delay}s…")
        self._timer.start(delay * 1000)

    def _reconnect(self) -> None:
        if not self._mpv or not self._url:
            return
        self.state_changed.emit("loading", "Reconectando…")
        try:
            self._mpv.play(self._url)
        except Exception as exc:
            self._error.emit(str(exc))
