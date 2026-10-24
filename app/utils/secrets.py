"""Proteção de URLs sensíveis em repouso.

Windows: DPAPI (CryptProtectData), vinculado ao usuário do Windows. Outro usuário ou outra máquina
não consegue descriptografar o banco copiado.
Linux/macOS: sem criptografia (o arquivo fica com permissão 0600).
"""
import base64
import logging

from app.config import IS_WINDOWS

log = logging.getLogger(__name__)
PREFIX = "dpapi:v1:"
_ENTROPY = b"GJ-Smart-TV/source-url/v1"


def _dpapi(data: bytes, protect: bool) -> bytes:  # pragma: no cover - só roda no Windows
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob),
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    def blob(b: bytes):
        buf = ctypes.create_string_buffer(b, len(b))
        return Blob(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    din, _keep1 = blob(data)
    ent, _keep2 = blob(_ENTROPY)
    out = Blob()
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    if not fn(ctypes.byref(din), None, ctypes.byref(ent), None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
        raise OSError(ctypes.get_last_error(), "DPAPI falhou")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(out.pbData, ctypes.c_void_p))


def protect(text: str) -> str:
    if not IS_WINDOWS or text.startswith(PREFIX):
        return text
    return PREFIX + base64.b64encode(_dpapi(text.encode("utf-8"), True)).decode("ascii")


def unprotect(value: str) -> str:
    """Valores sem prefixo (legados ou Linux) voltam como estão. Falha de DPAPI devolve ''."""
    if not value.startswith(PREFIX):
        return value
    if not IS_WINDOWS:
        return ""
    try:
        return _dpapi(base64.b64decode(value[len(PREFIX):]), False).decode("utf-8")
    except Exception as exc:
        log.error("Não foi possível descriptografar um dado salvo (%s). Cadastre a fonte novamente.",
                  type(exc).__name__)
        return ""
