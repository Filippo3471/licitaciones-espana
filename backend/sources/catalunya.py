"""Fuente adicional: Contractació Pública a Catalunya (Generalitat de
Catalunya / Consorci AOC), publicada como datos abiertos Socrata — API
pública, sin clave, límites generosos.

Dataset: "Contractació pública a Catalunya: publicacions a la Plataforma
de serveis de contractació pública" (id ybgg-dgi6).
https://analisi.transparenciacatalunya.cat/d/ybgg-dgi6
"""
from __future__ import annotations

import datetime as dt

import requests

from ..cpv import sector_legible
from ..nuts_es import ccaa_legible

URL = "https://analisi.transparenciacatalunya.cat/resource/ybgg-dgi6.json"
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)"}

TIPO_CONTRATO_MAP = {
    "Obres": "Obras",
    "Serveis": "Servicios",
    "Subministraments": "Suministros",
    "Concessió d'obres": "Concesión de obras",
    "Concessió de serveis": "Concesión de servicios",
    "Administratiu especial": "Administrativo especial",
    "Privat": "Privado",
}


def _to_float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def fetch(limit: int = 2500) -> list[dict]:
    hoy = dt.date.today().isoformat() + "T00:00:00.000"
    params = {
        "$where": f"fase_publicacio='Anunci de licitació' AND termini_presentacio_ofertes >= '{hoy}'",
        "$order": "termini_presentacio_ofertes ASC",
        "$limit": limit,
    }
    try:
        resp = requests.get(URL, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"[catalunya] fuente no disponible ahora mismo ({exc.__class__.__name__}): se omite")
        return []

    out = []
    for item in items:
        expediente = item.get("codi_expedient")
        titulo = item.get("denominacio")
        if not titulo:
            continue
        cpv = (item.get("codi_cpv") or "").split("-")[0].strip()
        nuts = item.get("codi_nuts")
        out.append(
            {
                "fuente": "Catalunya (Generalitat)",
                "external_id": f"cat-{item.get('id_intern')}",
                "expediente": expediente,
                "titulo": titulo,
                "objeto": item.get("objecte_contracte"),
                "organo": item.get("nom_organ"),
                "tipo_contrato_legible": TIPO_CONTRATO_MAP.get(item.get("tipus_contracte"), item.get("tipus_contracte")),
                "importe": _to_float(item.get("pressupost_licitacio_sense") or item.get("valor_estimat_contracte")),
                "sector": sector_legible(cpv) if cpv else "Sin clasificar",
                "ccaa": ccaa_legible(nuts) if nuts else "Cataluña",
                "ubicacion_nombre": item.get("lloc_execucio"),
                "ubicacion_nuts": nuts,
                "estado": "PUB",
                "estado_legible": "Abierta (plazo de presentación en curso)",
                "plazo_fecha": (item.get("termini_presentacio_ofertes") or "").split("T")[0] or None,
                "plazo_hora": (item.get("termini_presentacio_ofertes") or "").split("T")[1][:5] if "T" in (item.get("termini_presentacio_ofertes") or "") else None,
                "requisitos": [],
                "solvencia_tecnica": [],
                "solvencia_economica": [],
                "documentos": [],
                "detail_url": (item.get("enllac_publicacio") or {}).get("url"),
                "cpv_codes": [cpv] if cpv else [],
            }
        )
    return out
