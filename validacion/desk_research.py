"""Fase 1 de validación: investigación de escritorio sobre los datos que ya
tiene el MVP. Conecta en modo SOLO LECTURA a data/licitaciones.db (nunca
escribe) y calcula, por sector (división CPV de 2 dígitos) y por comunidad
autónoma:

  - nº de licitaciones abiertas hoy y su importe total/medio
  - frecuencia mensual de adjudicaciones (los últimos 12 meses completos)
  - cuota de adjudicaciones con pocos licitadores (competencia baja)

Limitación honesta: nuestro crawl de PLACSP empezó hace ~1 semana, así que
"licitaciones abiertas" es un snapshot fiel de hoy, pero el histórico de
adjudicaciones que trae el feed está sesgado hacia los meses recientes (el
feed de PLACSP no es un archivo histórico completo) — los meses más
antiguos casi seguro están infrarrepresentados. Se usan solo para dar una
cifra orientativa de frecuencia, no como serie temporal completa.

Uso:
    python3 validacion/desk_research.py
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.cpv import sector_legible

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "licitaciones.db"
OUT_JSON = Path(__file__).resolve().parent / "desk_research.json"

POCOS_LICITADORES_UMBRAL = 3  # <=3 ofertas se considera "poca competencia" (criterio explícito, no un estándar externo)
MESES_HISTORICO = 12


def get_readonly_conn():
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sector_de_cpv_codes(cpv_json: str | None) -> str:
    if not cpv_json:
        return "Sin clasificar"
    try:
        codes = json.loads(cpv_json)
    except (json.JSONDecodeError, TypeError):
        return "Sin clasificar"
    if not codes:
        return "Sin clasificar"
    return sector_legible(codes[0])


def analizar_por_sector(conn) -> list[dict]:
    abiertas = conn.execute(
        "SELECT cpv_codes, importe FROM licitaciones WHERE estado = 'PUB'"
    ).fetchall()

    hoy = dt.date.today()
    hace_12_meses = (hoy.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    for _ in range(MESES_HISTORICO - 1):
        hace_12_meses = (hace_12_meses.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    desde = hace_12_meses.isoformat()

    adjudicadas = conn.execute(
        """
        SELECT cpv_codes, num_licitadores, fecha_adjudicacion
        FROM licitaciones
        WHERE estado IN ('ADJ', 'RES')
          AND fecha_adjudicacion IS NOT NULL AND fecha_adjudicacion != ''
          AND fecha_adjudicacion >= ? AND fecha_adjudicacion <= ?
        """,
        (desde, hoy.isoformat()),
    ).fetchall()

    por_sector: dict[str, dict] = {}

    def bucket(sector):
        return por_sector.setdefault(sector, {
            "sector": sector,
            "abiertas_n": 0,
            "abiertas_importe_total": 0.0,
            "abiertas_importe_valores": [],
            "adjudicadas_12m_n": 0,
            "adjudicadas_con_pocos_licitadores_n": 0,
            "adjudicadas_con_dato_licitadores_n": 0,
        })

    for r in abiertas:
        sector = sector_de_cpv_codes(r["cpv_codes"])
        b = bucket(sector)
        b["abiertas_n"] += 1
        if r["importe"]:
            b["abiertas_importe_total"] += r["importe"]
            b["abiertas_importe_valores"].append(r["importe"])

    for r in adjudicadas:
        sector = sector_de_cpv_codes(r["cpv_codes"])
        b = bucket(sector)
        b["adjudicadas_12m_n"] += 1
        if r["num_licitadores"] is not None:
            b["adjudicadas_con_dato_licitadores_n"] += 1
            if r["num_licitadores"] <= POCOS_LICITADORES_UMBRAL:
                b["adjudicadas_con_pocos_licitadores_n"] += 1

    resultado = []
    for sector, b in por_sector.items():
        n_importes = len(b["abiertas_importe_valores"])
        n_lic = b["adjudicadas_con_dato_licitadores_n"]
        resultado.append({
            "sector": sector,
            "licitaciones_abiertas": b["abiertas_n"],
            "importe_total_abiertas_eur": round(b["abiertas_importe_total"], 2),
            "importe_medio_abiertas_eur": round(b["abiertas_importe_total"] / n_importes, 2) if n_importes else None,
            "adjudicadas_ultimos_12m": b["adjudicadas_12m_n"],
            "frecuencia_mensual_aprox": round(b["adjudicadas_12m_n"] / MESES_HISTORICO, 1),
            "pct_pocos_licitadores": round(100 * b["adjudicadas_con_pocos_licitadores_n"] / n_lic, 1) if n_lic else None,
            "n_adjudicadas_con_dato_licitadores": n_lic,
        })

    resultado.sort(key=lambda x: x["importe_total_abiertas_eur"], reverse=True)
    return resultado


def analizar_por_ccaa(conn, sectores_objetivo: list[str]) -> list[dict]:
    abiertas = conn.execute(
        "SELECT cpv_codes, importe, ccaa FROM licitaciones WHERE estado = 'PUB'"
    ).fetchall()
    por_combo: dict[tuple, dict] = {}
    for r in abiertas:
        sector = sector_de_cpv_codes(r["cpv_codes"])
        if sector not in sectores_objetivo:
            continue
        ccaa = r["ccaa"] or "Sin especificar"
        key = (sector, ccaa)
        b = por_combo.setdefault(key, {"sector": sector, "ccaa": ccaa, "licitaciones_abiertas": 0, "importe_total_eur": 0.0})
        b["licitaciones_abiertas"] += 1
        if r["importe"]:
            b["importe_total_eur"] += r["importe"]
    resultado = list(por_combo.values())
    for r in resultado:
        r["importe_total_eur"] = round(r["importe_total_eur"], 2)
    resultado.sort(key=lambda x: (x["sector"], -x["licitaciones_abiertas"]))
    return resultado


def main():
    conn = get_readonly_conn()
    try:
        por_sector = analizar_por_sector(conn)
        top_por_importe = [s for s in por_sector if s["licitaciones_abiertas"] >= 20][:8]
        # Los 2 sectores objetivo elegidos (hipotesis.md) deben ir siempre en el
        # desglose por CCAA aunque no entren en el top-8 bruto por importe —
        # si no, cualquier consumidor de este archivo (p.ej. la Fase 4) se
        # queda sin datos de CCAA justo para los sectores que sí importan.
        SECTORES_OBJETIVO = [
            "Servicios de arquitectura, ingeniería y construcción",
            "Servicios de tecnologías de la información (TI)",
        ]
        # Explorados el 28/09/2026 a petición explícita de ampliar el
        # reclutamiento a otras industrias (Fase 4) — no son una redefinición
        # de los 2 sectores objetivo de hipotesis.md, solo candidatos
        # adicionales con el mismo criterio cuantitativo, no por intuición.
        SECTORES_ADICIONALES_EXPLORADOS = [
            "Servicios empresariales: publicidad, limpieza, consultoría, seguridad",
            "Servicios medioambientales, saneamiento, residuos",
        ]
        sectores_objetivo_candidatos = sorted(set(
            [s["sector"] for s in top_por_importe] + SECTORES_OBJETIVO + SECTORES_ADICIONALES_EXPLORADOS
        ))
        por_ccaa = analizar_por_ccaa(conn, sectores_objetivo_candidatos)
    finally:
        conn.close()

    payload = {
        "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
        "nota_metodologica": (
            "Lectura de solo-lectura de data/licitaciones.db. 'Abiertas' es un "
            "snapshot del momento de ejecución. 'Adjudicadas últimos 12 meses' "
            "usa fecha_adjudicacion del feed de PLACSP, que está sesgado hacia "
            "meses recientes (no es un archivo histórico completo) — la "
            "frecuencia mensual es orientativa, no una serie temporal fiable "
            "mes a mes. 'Pocos licitadores' = <= "
            f"{POCOS_LICITADORES_UMBRAL} ofertas recibidas, umbral propio."
        ),
        "por_sector": por_sector,
        "por_sector_y_ccaa_top_candidatos": por_ccaa,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Guardado {OUT_JSON}")
    print("\nTop 10 sectores por importe total de licitaciones abiertas:")
    for s in por_sector[:10]:
        print(
            f"  {s['sector']:<55} abiertas={s['licitaciones_abiertas']:>4}  "
            f"importe_total={s['importe_total_abiertas_eur']:>15,.0f}€  "
            f"frec/mes~{s['frecuencia_mensual_aprox']:>5}  "
            f"%pocos_licitadores={s['pct_pocos_licitadores']}"
        )


if __name__ == "__main__":
    main()
