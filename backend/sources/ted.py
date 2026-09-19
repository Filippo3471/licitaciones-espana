"""Fuente adicional: TED (Tenders Electronic Daily), el diario oficial de
licitaciones de la UE por encima de los umbrales europeos. API pública de
búsqueda (Search API v3), sin necesidad de clave.

Documentación: https://developer.ted.europa.eu/
Endpoint: POST https://api.ted.europa.eu/v3/notices/search
"""
from __future__ import annotations

import requests

from ..cpv import sector_legible
from ..nuts_es import ccaa_legible

URL = "https://api.ted.europa.eu/v3/notices/search"
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)", "Content-Type": "application/json"}

FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "deadline-receipt-tender-date-lot",
    "estimated-value-lot",
    "estimated-value-cur-lot",
    "classification-cpv",
    "place-of-performance-subdiv-lot",
    "place-of-performance-city-lot",
]

QUERY = "buyer-country=ESP AND notice-type=cn-standard SORT BY publication-date DESC"


def _pick_lang(field, langs=("spa", "eng")):
    """Los campos de texto de TED vienen en ~24 idiomas; nos quedamos con
    español (o inglés si no está) y descartamos el resto."""
    if not isinstance(field, dict):
        return None
    for lang in langs:
        if lang in field and field[lang]:
            val = field[lang]
            return val[0] if isinstance(val, list) else val
    for val in field.values():
        return val[0] if isinstance(val, list) else val
    return None


def _first(field):
    if isinstance(field, list):
        return field[0] if field else None
    return field


def fetch(max_pages: int = 4, page_size: int = 250) -> list[dict]:
    out = []
    try:
        for page in range(1, max_pages + 1):
            body = {"query": QUERY, "fields": FIELDS, "limit": page_size, "page": page}
            resp = requests.post(URL, headers=HEADERS, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            notices = data.get("notices") or []
            if not notices:
                break
            for n in notices:
                out.append(_normalize(n))
    except (requests.RequestException, ValueError) as exc:
        print(f"[ted] fuente no disponible ahora mismo ({exc.__class__.__name__}): se omite")
        return [r for r in out if r]
    return [r for r in out if r]


def _normalize(n: dict) -> dict | None:
    pub_number = n.get("publication-number")
    title = _pick_lang(n.get("notice-title"))
    if not pub_number or not title:
        return None

    buyer = _pick_lang(n.get("buyer-name"))
    deadline = _first(n.get("deadline-receipt-tender-date-lot"))
    plazo_fecha = deadline.split("+")[0].split("T")[0] if deadline else None

    importe = None
    valores = n.get("estimated-value-lot")
    if valores:
        try:
            importe = float(_first(valores))
        except (TypeError, ValueError):
            importe = None

    cpv_codes = [c for c in (n.get("classification-cpv") or []) if c]
    ciudad = _first(n.get("place-of-performance-city-lot"))
    nuts = _first(n.get("place-of-performance-subdiv-lot"))

    return {
        "fuente": "TED (UE)",
        "external_id": f"ted-{pub_number}",
        "expediente": pub_number,
        "titulo": title,
        "objeto": title,
        "organo": buyer or "No especificado",
        "tipo_contrato_legible": None,
        "importe": importe,
        "sector": sector_legible(cpv_codes[0]) if cpv_codes else "Sin clasificar",
        "ccaa": ccaa_legible(nuts) if nuts else "España (sin especificar)",
        "ubicacion_nombre": ciudad,
        "ubicacion_nuts": nuts,
        "estado": "PUB",
        "estado_legible": "Abierta (plazo de presentación en curso)",
        "plazo_fecha": plazo_fecha,
        "plazo_hora": None,
        "requisitos": [],
        "solvencia_tecnica": [],
        "solvencia_economica": [],
        "documentos": [],
        "detail_url": f"https://ted.europa.eu/es/notice/-/detail/{pub_number}",
        "cpv_codes": [c for c in cpv_codes if c],
    }
