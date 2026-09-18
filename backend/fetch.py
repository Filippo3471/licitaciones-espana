"""Descarga de los feeds ATOM/CODICE de la Plataforma de Contratación del
Sector Público (PLACSP - contrataciondelestado.es).

Nota sobre TLS: el certificado del sitio está emitido por la CA "AC RAIZ
FNMT-RCM SERVIDORES SEGUROS" (FNMT, la Fábrica Nacional de Moneda y Timbre,
autoridad de certificación oficial del Estado español). Ese root no está
incluido en el almacén de confianza por defecto de macOS/curl en muchos
sistemas fuera de España, así que lo añadimos explícitamente en vez de
desactivar la verificación TLS (nunca usamos verify=False).
"""
from __future__ import annotations

import time
from pathlib import Path

import certifi
import requests

FEED_URL = (
    "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3.atom"
)

CERTS_DIR = Path(__file__).resolve().parent / "certs"
_COMBINED_BUNDLE = Path(__file__).resolve().parent.parent / "data" / "ca-bundle.pem"

HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)"}


def _combined_ca_bundle() -> str:
    """Certifi (CAs públicas estándar) + la cadena FNMT de contrataciondelestado.es."""
    _COMBINED_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    if not _COMBINED_BUNDLE.exists():
        base = Path(certifi.where()).read_text()
        extra = (CERTS_DIR / "fnmt_intermediate.pem").read_text() + (
            CERTS_DIR / "fnmt_root.pem"
        ).read_text()
        _COMBINED_BUNDLE.write_text(base + "\n" + extra)
    return str(_COMBINED_BUNDLE)


def fetch_page(url: str, timeout: int = 45, retries: int = 3) -> bytes:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=_combined_ca_bundle())
            resp.raise_for_status()
            return resp.content
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            if attempt < retries:
                wait = 3 * attempt
                print(f"  [fetch] intento {attempt}/{retries} falló ({exc.__class__.__name__}), reintentando en {wait}s...")
                time.sleep(wait)
    raise last_exc


def iter_pages(start_url: str = FEED_URL, max_pages: int = 10, delay: float = 1.0):
    """Descarga páginas siguiendo rel=next, hasta max_pages (cortesía: pausa
    entre peticiones para no sobrecargar el servidor público)."""
    from . import parser

    url = start_url
    for i in range(max_pages):
        content = fetch_page(url)
        yield content
        nxt = parser.next_link(content)
        if not nxt:
            break
        url = nxt
        time.sleep(delay)
