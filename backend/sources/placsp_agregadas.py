"""PLACSP — Plataformas agregadas (sindicacion_1044): licitaciones de
entidades SIN perfil de contratante propio en PLACSP, que publican a
través de plataformas de comunidades autónomas, diputaciones y otros
entes territoriales (Catalunya, País Vasco, Andalucía, Madrid, Galicia,
Navarra, La Rioja... la lista cambia). El feed principal que ya usamos
(sindicacion_643) NO incluye estas — son licitaciones de verdad, con el
mismo vocabulario de estados (PUB/EV/ADJ/RES/ANUL/PRE) que el feed
principal, así que se integran en la misma tabla SQLite y el resto del
pipeline (export.py) las trata igual, sin cambios.

No incluye contratos menores (eso va en un feed aparte, sindicacion_1143,
que no se integra aquí: un contrato menor se adjudica directo, sin
proceso competitivo — no hay oferta que preparar, no encaja en GO/NO-GO).

Formato: un ZIP mensual con varios ficheros .atom dentro (snapshots
diarios del mes), mismo esquema CODICE que el feed principal — se
reutiliza el parser existente (backend/parser.py) tal cual.

Verificado en vivo el 15-10-2026: el ZIP del mes actual puede no existir
todavía (se publica con unos días de margen) — se prueba el mes actual y,
si no existe, el anterior.
"""
from __future__ import annotations

import datetime as dt
import io
import zipfile

import requests

from .. import cpv as cpv_mod
from .. import nuts_es, parser
from ..db import upsert
from ..fetch import HEADERS, _combined_ca_bundle

BASE = "https://contrataciondelestado.es/sindicacion/sindicacion_1044/PlataformasAgregadasSinMenores_{ym}.zip"


def _descargar_zip(year_month: str) -> zipfile.ZipFile | None:
    url = BASE.format(ym=year_month)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=90, verify=_combined_ca_bundle())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return zipfile.ZipFile(io.BytesIO(resp.content))
    except (requests.RequestException, zipfile.BadZipFile) as exc:
        print(f"[placsp_agregadas] {year_month} no disponible ({exc.__class__.__name__}): se omite")
        return None


def sync(conn, meses_atras: int = 2) -> int:
    """Descarga los últimos `meses_atras` meses (el actual y los
    anteriores) y hace upsert de cada entrada en la misma tabla
    `licitaciones`. Devuelve cuántas entradas se procesaron."""
    hoy = dt.date.today()
    fetched_at = dt.datetime.now().isoformat(timespec="seconds")
    total = 0
    cursor = hoy.replace(day=1)  # primer día del mes actual
    for i in range(meses_atras):
        mes = cursor
        for _ in range(i):
            mes = (mes - dt.timedelta(days=1)).replace(day=1)  # un mes atrás por iteración
        ym = mes.strftime("%Y%m")

        z = _descargar_zip(ym)
        if z is None:
            continue
        for name in z.namelist():
            if not name.endswith(".atom"):
                continue
            content = z.read(name)
            for row in parser.iter_entries(content):
                sector = cpv_mod.sector_legible(row["cpv_codes"][0]) if row["cpv_codes"] else "Sin clasificar"
                ccaa = nuts_es.ccaa_legible(row["ubicacion_nuts"])
                upsert(conn, row, sector=sector, ccaa=ccaa, fetched_at=fetched_at)
                total += 1
        conn.commit()
        print(f"[placsp_agregadas] {ym}: {len(z.namelist())} ficheros procesados")
    return total
