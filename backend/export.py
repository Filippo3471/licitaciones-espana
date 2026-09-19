"""Combina todas las fuentes (PLACSP + Bilbao + TendersGuru) en un único
JSON compacto, listo para incrustar en el sitio de búsqueda.

Uso:
    python -m backend.export --pages 15 --out data/licitaciones.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from . import update as placsp_update
from .db import get_conn
from .sources import bilbao, tenders_guru

OUT_DEFAULT = Path(__file__).resolve().parent.parent / "data" / "licitaciones.json"


def _placsp_rows() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM licitaciones WHERE estado = 'PUB'").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        for f in ("cpv_codes", "requisitos", "solvencia_tecnica", "solvencia_economica", "documentos"):
            d[f] = json.loads(d[f]) if d[f] else []
        out.append(
            {
                "fuente": "PLACSP",
                "external_id": d["external_id"],
                "expediente": d["expediente"],
                "titulo": d["titulo"],
                "objeto": d["objeto"],
                "organo": d["organo"],
                "tipo_contrato_legible": _tipo_contrato(d["tipo_contrato_code"]),
                "importe": d["importe"],
                "sector": d["sector"],
                "ccaa": d["ccaa"],
                "ubicacion_nombre": d["ubicacion_nombre"],
                "estado": d["estado"],
                "estado_legible": "Abierta (plazo de presentación en curso)",
                "plazo_fecha": d["plazo_fecha"],
                "plazo_hora": d["plazo_hora"],
                "requisitos": d["requisitos"],
                "solvencia_tecnica": d["solvencia_tecnica"],
                "solvencia_economica": d["solvencia_economica"],
                "documentos": d["documentos"],
                "detail_url": d["detail_url"],
                "cpv_codes": d["cpv_codes"],
            }
        )
    return out


def _tipo_contrato(code: str | None) -> str:
    from .codelists import tipo_contrato_legible

    return tipo_contrato_legible(code)


ESTADO_ADJUDICACION_LEGIBLE = {
    "ADJ": "Adjudicada",
    "RES": "Resuelta / formalizada",
}


def _adjudicaciones_rows(limit: int = 4000) -> list[dict]:
    """Histórico de adjudicaciones: quién ganó cada licitación, por cuánto y
    con cuántos competidores. Se ordena por fecha de adjudicación descendente
    y se limita para mantener el tamaño del JSON manejable — la base de
    datos local conserva todo, así que este histórico se hace más rico con
    cada ejecución programada."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM licitaciones
        WHERE estado IN ('ADJ', 'RES') AND adjudicatario_nombre IS NOT NULL
        ORDER BY (fecha_adjudicacion IS NULL), fecha_adjudicacion DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        cpv_codes = json.loads(d["cpv_codes"]) if d["cpv_codes"] else []
        out.append(
            {
                "fuente": "PLACSP",
                "external_id": d["external_id"],
                "expediente": d["expediente"],
                "titulo": d["titulo"],
                "organo": d["organo"],
                "tipo_contrato_legible": _tipo_contrato(d["tipo_contrato_code"]),
                "sector": d["sector"],
                "ccaa": d["ccaa"],
                "ubicacion_nombre": d["ubicacion_nombre"],
                "estado": d["estado"],
                "estado_legible": ESTADO_ADJUDICACION_LEGIBLE.get(d["estado"], d["estado"]),
                "importe_licitacion": d["importe"],
                "importe_adjudicacion": d["importe_adjudicacion"],
                "fecha_adjudicacion": d["fecha_adjudicacion"],
                "num_licitadores": d["num_licitadores"],
                "num_pymes_licitadoras": d["num_pymes_licitadoras"],
                "adjudicatario_nombre": d["adjudicatario_nombre"],
                "adjudicatario_nif": d["adjudicatario_nif"],
                "adjudicatario_ciudad": d["adjudicatario_ciudad"],
                "adjudicatario_ccaa": d["adjudicatario_ccaa"],
                "detail_url": d["detail_url"],
                "cpv_codes": cpv_codes,
            }
        )
    return out


def run(
    pages: int,
    out_path: Path,
    refresh_placsp: bool = True,
    include_optional_sources: bool = True,
    adjudicaciones_out_path: Path | None = None,
):
    if refresh_placsp:
        print("Actualizando PLACSP...")
        placsp_update.run(max_pages=pages)

    registros = _placsp_rows()
    conteo = {"PLACSP": len(registros)}

    if include_optional_sources:
        for nombre, fn in (("Bilbao", bilbao.fetch), ("TendersGuru", tenders_guru.fetch)):
            try:
                extra = fn()
            except Exception as exc:  # fuente externa: nunca debe tumbar el export
                print(f"[{nombre}] error inesperado, se omite: {exc}")
                extra = []
            conteo[nombre] = len(extra)
            registros.extend(extra)

    payload = {
        "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
        "total": len(registros),
        "por_fuente": conteo,
        "licitaciones": registros,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(f"\nExportado {len(registros)} licitaciones a {out_path}")
    for f, n in conteo.items():
        print(f"  {f}: {n}")

    adjudicaciones = _adjudicaciones_rows()
    adj_path = adjudicaciones_out_path or (out_path.parent / "adjudicaciones.json")
    adj_payload = {
        "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
        "total": len(adjudicaciones),
        "adjudicaciones": adjudicaciones,
    }
    adj_path.write_text(json.dumps(adj_payload, ensure_ascii=False, separators=(",", ":")))
    print(f"Exportadas {len(adjudicaciones)} adjudicaciones a {adj_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Exporta todas las fuentes a un JSON unificado")
    ap.add_argument("--pages", type=int, default=15, help="Páginas del feed PLACSP a descargar")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--no-refresh-placsp", action="store_true", help="No re-descargar PLACSP, usar la BD tal cual")
    ap.add_argument("--no-optional-sources", action="store_true", help="Omitir Bilbao/TendersGuru")
    args = ap.parse_args()
    run(
        pages=args.pages,
        out_path=args.out,
        refresh_placsp=not args.no_refresh_placsp,
        include_optional_sources=not args.no_optional_sources,
    )
