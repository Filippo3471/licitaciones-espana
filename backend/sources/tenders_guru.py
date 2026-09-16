"""Fuente adicional: TendersGuru (https://tenders.guru/es/api), un agregador
de terceros (no oficial) listado en github.com/public-apis/public-apis.

Endpoints documentados:
  GET https://tenders.guru/api/es/tenders
  GET https://tenders.guru/api/es/tenders/{id}
  GET https://tenders.guru/api/es/tenders/{id}/docs

A fecha de implementación el servicio no respondía (conexión rechazada), así
que esta integración es defensiva por diseño: si falla o el esquema JSON no
coincide con lo esperado, se ignora en silencio y el resto del pipeline sigue
funcionando con las demás fuentes. Cuando el servicio vuelva a estar
disponible conviene revisar el mapeo de campos contra la respuesta real.
"""
from __future__ import annotations

import requests

BASE = "https://tenders.guru/api/es"
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)"}


def fetch(max_pages: int = 5) -> list[dict]:
    out = []
    try:
        for page in range(1, max_pages + 1):
            resp = requests.get(f"{BASE}/tenders", params={"page": page}, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or data.get("data") or data.get("tenders") or []
            if not results:
                break
            for item in results:
                out.append(_normalize(item))
            if not data.get("next") and len(results) < 20:
                break
    except (requests.RequestException, ValueError) as exc:
        print(f"[tenders_guru] fuente no disponible ahora mismo ({exc.__class__.__name__}): se omite")
        return []
    return [r for r in out if r]


def _normalize(item: dict) -> dict | None:
    tid = item.get("id") or item.get("tender_id")
    title = item.get("title") or item.get("name")
    if not tid or not title:
        return None
    return {
        "fuente": "TendersGuru",
        "external_id": f"tendersguru-{tid}",
        "expediente": str(tid),
        "titulo": title,
        "objeto": item.get("description"),
        "organo": item.get("buyer") or item.get("organization") or "No especificado",
        "tipo_contrato_legible": item.get("type") or "No especificado",
        "importe": item.get("value") or item.get("budget"),
        "sector": item.get("category") or "Sin clasificar",
        "ccaa": item.get("region") or "España (sin especificar)",
        "ubicacion_nombre": item.get("location"),
        "estado": "PUB",
        "estado_legible": "Abierta (plazo de presentación en curso)",
        "plazo_fecha": item.get("closing_date") or item.get("deadline"),
        "requisitos": [],
        "solvencia_tecnica": [],
        "solvencia_economica": [],
        "documentos": [],
        "detail_url": item.get("url") or f"https://tenders.guru/es/tender/{tid}",
    }
