"""Orquestador: descarga páginas del feed de PLACSP, parsea cada licitación y
la guarda/actualiza en SQLite.

Uso:
    python -m backend.update --pages 15
"""
import argparse
import datetime as dt

from . import cpv, fetch, nuts_es, parser
from .db import get_conn, upsert


def run(max_pages: int = 10):
    conn = get_conn()
    fetched_at = dt.datetime.now().isoformat(timespec="seconds")
    total = 0
    por_estado: dict[str, int] = {}

    for page_num, page in enumerate(fetch.iter_pages(max_pages=max_pages), start=1):
        entries = list(parser.iter_entries(page))
        for row in entries:
            sector = cpv.sector_legible(row["cpv_codes"][0]) if row["cpv_codes"] else "Sin clasificar"
            ccaa = nuts_es.ccaa_legible(row["ubicacion_nuts"])
            upsert(conn, row, sector=sector, ccaa=ccaa, fetched_at=fetched_at)
            total += 1
            por_estado[row["estado"]] = por_estado.get(row["estado"], 0) + 1
        conn.commit()
        print(f"Página {page_num}: {len(entries)} licitaciones procesadas")

    print(f"\nTotal procesado: {total}")
    for estado, n in sorted(por_estado.items(), key=lambda x: -x[1]):
        print(f"  {estado}: {n}")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Actualiza la base de datos de licitaciones desde PLACSP")
    ap.add_argument("--pages", type=int, default=10, help="Número de páginas del feed a descargar (500 entradas por página aprox.)")
    args = ap.parse_args()
    run(max_pages=args.pages)
