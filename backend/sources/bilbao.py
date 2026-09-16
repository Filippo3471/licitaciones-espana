"""Fuente adicional: licitaciones en plazo abierto del Ayuntamiento de Bilbao
(Open Data Euskadi / Bilbao Open Data). No está garantizado que sea disjunta
de la PLACSP (algunos ayuntamientos publican en ambas), pero es una fuente
oficial legítima y a veces llega antes o con más detalle municipal.

Endpoint: https://www.bilbao.eus/opendata/datos/licitaciones
"""
from __future__ import annotations

import requests

URL = "https://www.bilbao.eus/opendata/datos/licitaciones"
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)"}


def _to_float(s: str | None):
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def fetch() -> list[dict]:
    """Devuelve licitaciones en plazo abierto, normalizadas al esquema común."""
    resp = requests.get(
        URL, params={"formato": "json", "estados": 3, "idioma": "es"}, headers=HEADERS, timeout=20
    )
    resp.raise_for_status()
    data = resp.json()
    out = []
    for item in data.get("licitaciones", []):
        expediente = item.get("N_Expediente")
        if not expediente:
            continue
        out.append(
            {
                "fuente": "Ayuntamiento de Bilbao",
                "external_id": f"bilbao-{expediente}",
                "expediente": expediente,
                "titulo": item.get("Objeto") or "(sin título)",
                "objeto": item.get("Objeto"),
                "organo": "Ayuntamiento de Bilbao"
                + (f" — {item['Area_Municipal_promotora_del_Expediente']}" if item.get("Area_Municipal_promotora_del_Expediente") else ""),
                "tipo_contrato_legible": item.get("Tipo_Contrato"),
                "importe": _to_float(item.get("Presupuesto_de_licitacion_IVA_Excluido")),
                "sector": "Sin clasificar (fuente municipal)",
                "ccaa": "País Vasco",
                "ubicacion_nombre": "Bilbao (Bizkaia)",
                "estado": "PUB",
                "estado_legible": "Abierta (plazo de presentación en curso)",
                "plazo_fecha": None,
                "requisitos": [],
                "solvencia_tecnica": [],
                "solvencia_economica": [],
                "documentos": [],
                "detail_url": "https://www.bilbao.eus/cs/Satellite/contratacionAdministrativa",
            }
        )
    return out
