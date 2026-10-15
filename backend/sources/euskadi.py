"""Fuente adicional: KontratazioA, la plataforma de contratación pública
de Euskadi (Gobierno Vasco) — API REST de Open Data Euskadi sobre el
Registro de Contratos del Sector Público de Euskadi (REVASCON). Pública,
sin clave, documentada en formato OpenAPI.

Base: https://api.euskadi.eus/procurements/contracting-notices
Verificada en vivo el 15-10-2026: ~722.000 anuncios totales, 628 con
estado 3 ("Abierto / Plazo de presentación") en el momento de probarlo.

Aviso de calidad de datos real (no es un bug nuestro): algunos anuncios
antiguos quedan marcados como estado 3 aunque su deadlineDate ya pasó
hace años — el filtro global de licitaciones.json (plazo_fecha >= hoy,
en export.py) descarta estos de todas formas, así que no hace falta
duplicar esa lógica aquí.

No incluye contratos menores (minorContract=true): esos se adjudican
directo, sin proceso competitivo — no hay oferta que preparar.
"""
from __future__ import annotations

import requests

from ..cpv import sector_legible
from ..nuts_es import ccaa_legible

BASE_URL = "https://api.euskadi.eus/procurements/contracting-notices"
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)", "Accept": "application/json"}
ESTADO_ABIERTO = 3
ITEMS_POR_PAGINA = 50


def fetch(max_pages: int = 20) -> list[dict]:
    """Hasta max_pages * 50 anuncios abiertos (20*50=1000, de sobra para
    los ~600 que suele haber abiertos a la vez)."""
    out = []
    page = 1
    for _ in range(max_pages):
        try:
            resp = requests.get(
                BASE_URL,
                headers=HEADERS,
                params={
                    "contract-procedure-status-id": ESTADO_ABIERTO,
                    "minor-contract": "false",
                    "currentPage": page,
                    "itemsOfPage": ITEMS_POR_PAGINA,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[euskadi] fuente no disponible ahora mismo ({exc.__class__.__name__}): se omite")
            break

        for item in data.get("items", []):
            out.append(_a_fila(item))

        if not data.get("_links", {}).get("next") or page >= data.get("totalPages", 0):
            break
        page += 1

    return out


def _a_fila(item: dict) -> dict:
    org = item.get("contractingAuthority") or {}
    tipo = (item.get("contractType") or {}).get("name")
    return {
        "fuente": "País Vasco (KontratazioA)",
        "external_id": f"eusk-{item.get('id')}",
        "expediente": item.get("code"),
        "titulo": item.get("object"),
        "objeto": item.get("object"),
        "organo": org.get("name"),
        "tipo_contrato_legible": tipo,
        "importe": item.get("budgetWithoutVAT"),
        # La API no da el CPV del anuncio concreto en este endpoint — se
        # deja sin clasificar en vez de adivinarlo (igual que las demás
        # fuentes cuando no hay CPV).
        "sector": "Sin clasificar",
        "ccaa": ccaa_legible(org.get("codNUTS")) if org.get("codNUTS") else "País Vasco",
        "ubicacion_nombre": org.get("address"),
        "ubicacion_nuts": org.get("codNUTS"),
        "estado": "PUB",
        "estado_legible": "Abierta (plazo de presentación en curso)",
        "plazo_fecha": item.get("deadlineDate"),
        "plazo_hora": None,
        "requisitos": [],
        "solvencia_tecnica": [],
        "solvencia_economica": [],
        "documentos": [],
        "detail_url": (item.get("_links") or {}).get("self", {}).get("href") or item.get("webpagElectronicBidding"),
        "cpv_codes": [],
    }
