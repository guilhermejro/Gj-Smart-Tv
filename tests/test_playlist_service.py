import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest
from app.services.playlist_service import PlaylistError, load_playlist

BODY = "#EXTM3U\n#EXTINF:-1 group-title=\"G\",Canal\nhttp://s/1.m3u8\n".encode()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/ok.m3u":
            self.send_response(200); self.send_header("Content-Length", str(len(BODY))); self.end_headers(); self.wfile.write(BODY)
        elif self.path == "/redir":
            self.send_response(302); self.send_header("Location", "file:///etc/passwd"); self.end_headers()
        elif self.path == "/html":
            self.send_response(200); self.end_headers(); self.wfile.write(b"<html></html>")
        else:
            self.send_response(404); self.end_headers()


@pytest.fixture(scope="module")
def base():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_ok(base):
    assert load_playlist(base + "/ok.m3u").total == 1


def test_404(base):
    with pytest.raises(PlaylistError, match="404"):
        load_playlist(base + "/nada")


def test_redirect_para_esquema_proibido(base):
    with pytest.raises(PlaylistError):
        load_playlist(base + "/redir")


def test_incompativel(base):
    with pytest.raises(PlaylistError, match="M3U"):
        load_playlist(base + "/html")


def test_inacessivel():
    with pytest.raises(PlaylistError):
        load_playlist("http://127.0.0.1:9/x.m3u")
