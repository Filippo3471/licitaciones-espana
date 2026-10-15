"""Castilla y León — "Contratos ordinarios", Datos Abiertos de la Junta
de Castilla y León (datosabiertos.jcyl.es). CSV público, sin clave.

Verificado en vivo el 15-10-2026: 9.854 filas, formalizaciones desde
2019-01-04 hasta 2026-09-30 (vivo, no parado).

AVISO IMPORTANTE: a diferencia de Euskadi/PLACSP-agregadas, este dataset
NO son licitaciones abiertas — son contratos YA FORMALIZADOS (tiene
"Fecha Formalización", adjudicatario, NIF, importe de adjudicación; no
tiene plazo de presentación de ofertas). No hay nada que una empresa
pueda "presentar" aquí. Por eso se integra como ADJUDICACIONES (para
enriquecer "quién gana en tu sector"), no como licitaciones abiertas —
no suma al contador de licitaciones abiertas ni sirve para GO/NO-GO.

El portal exige una cookie de sesión (se obtiene visitando antes la
página del dataset) — con una request.Session() normal basta, no hace
falta navegador.
"""
from __future__ import annotations

import csv
import datetime as dt
import io

import requests

from ..db import upsert

PAGINA_DATASET = "https://datosabiertos.jcyl.es/web/jcyl/set/es/sector-publico/contratos-ordinarios/1284923806877"
URL_CSV = "https://datosabiertos.jcyl.es/web/jcyl/risp/es/sector-publico/contratos-ordinarios/1284923806877.csv"
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo local)"}


def _to_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _to_int(v: str | None) -> int | None:
    try:
        return int(v) if v else None
    except ValueError:
        return None


def sync(conn) -> int:
    fetched_at = dt.datetime.now().isoformat(timespec="seconds")
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get(PAGINA_DATASET, timeout=30)  # recoge la cookie de sesión
        resp = s.get(URL_CSV, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[castilla_y_leon] fuente no disponible ahora mismo ({exc.__class__.__name__}): se omite")
        return 0

    texto = resp.content.decode("utf-8-sig")
    lector = csv.DictReader(io.StringIO(texto), delimiter=";")

    total = 0
    for fila in lector:
        codigo = (fila.get("Código Contrato") or "").strip()
        titulo = (fila.get("Título") or "").strip()
        if not codigo or not titulo:
            continue
        row = {
            "fuente": "Castilla y León (Junta)",
            "external_id": f"cyl-{codigo}",
            "expediente": codigo,
            "updated": fetched_at,
            "titulo": titulo,
            "objeto": titulo,
            "organo": fila.get("Órgano"),
            "tipo_organo_code": None,
            "tipo_contrato_code": None,
            "pyme_adjudicado": None,
            "importe": _to_float(fila.get("Presupuesto de Licitación (IVA incluido)")),
            "ubicacion_nombre": None,
            "ubicacion_nuts": None,
            "estado": "RES",
            "plazo_fecha": None,
            "plazo_hora": None,
            "requisitos": [],
            "solvencia_tecnica": [],
            "solvencia_economica": [],
            "documentos": [],
            "detail_url": fila.get("Enlace de publicación"),
            "cpv_codes": [],
            "fecha_adjudicacion": fila.get("Fecha Formalización"),
            "importe_adjudicacion": _to_float(fila.get("Presupuesto de Adjudicación (IVA incluido)")),
            "num_licitadores": _to_int(fila.get("Nº Ofertas Presentadas")),
            "adjudicatario_nombre": fila.get("Identidad del adjudicatario"),
            "adjudicatario_nif": fila.get("NIF Adjudicatario"),
        }
        upsert(conn, row, sector="Sin clasificar", ccaa="Castilla y León", fetched_at=fetched_at)
        total += 1
    conn.commit()
    return total
