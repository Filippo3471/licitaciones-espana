"""Traspaso Harvey → Instantly (Opción B del plan de outreach de octubre).

Lee los prospectos ya sourceados y verificados por Harvey (DataForSEO +
Reoon, en ~/harvey/data/harvey.db), que Harvey deja en su propia base de
datos — este script NO toca esa base, solo lee. Para cada uno nuevo (que
no se haya exportado ya, controlado por .ya_exportados.json en este mismo
directorio):

  1. Calcula sector/ccaa reales (sector ya viene en el taxonomy correcto
     desde Harvey para los sourceados de adjudicatarios; para los nuevos
     de DataForSEO se usa tal cual si coincide, o "Sin clasificar" si no).
  2. Pide a licitaciones.json (el mismo JSON público que sirve la web, la
     misma fuente que usa la entrevista real en producción —
     _shared/informe_sector.ts — para que el número del email y el de la
     entrevista nunca se contradigan) el nº real de licitaciones abiertas
     y el importe total para ese sector+ccaa exactos. Sin red, sin esto,
     no se exporta esa fila (nunca se inventa un número).
  3. Inserta una fila nueva en validacion_empresas (Supabase) con un token
     real, estado "preparada" (nada se ha enviado).
  4. Escribe un CSV con el mismo formato que lote_02/03/04, listo para
     importar en Instantly.

NO envía nada. Solo lee de Harvey, lee de licitaciones.json, y escribe en
Supabase + un CSV local.

Requiere (igual que import_outreach_contacts.py):
    export SUPABASE_URL=https://fssriztfcedgmwtgkxof.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=...

Uso:
    .venv/bin/python validacion/harvey_a_lote.py --lote-id lote-05-dataforseo-2026-10-24 [--dry-run] [--limite 100]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import secrets
import sqlite3
import sys
from pathlib import Path

import requests

VALIDACION_DIR = Path(__file__).resolve().parent
HARVEY_DB = Path.home() / "harvey" / "data" / "harvey.db"
YA_EXPORTADOS = VALIDACION_DIR / ".ya_exportados.json"
LICITACIONES_JSON_URL = "https://filippo3471.github.io/licitaciones-espana/licitaciones.json"

# Sectores reales del proyecto (backend/cpv.py sector_legible) — si el
# "industry" que trae Harvey/DataForSEO no es exactamente uno de estos,
# se deja "Sin clasificar" en vez de adivinar.
SECTORES_VALIDOS = {
    "Construcción y obra civil", "Servicios de arquitectura, ingeniería y construcción",
    "Servicios empresariales: publicidad, limpieza, consultoría, seguridad",
    "Servicios de reparación y mantenimiento", "Sin clasificar",
    "Servicios medioambientales, saneamiento, residuos",
    "Equipos médicos, farmacia, cosmética", "Vehículos, transporte",
    "Servicios de tecnologías de la información (TI)", "Servicios de salud y acción social",
    "Paquetes de software y sistemas de información", "Materiales de construcción",
    "Mobiliario, artículos del hogar, limpieza", "Máquinas de oficina, informática",
    "Maquinaria y aparatos eléctricos", "Servicios de educación y formación",
    "Servicios de hostelería y restauración",
    "Productos petrolíferos, combustibles, electricidad y energía",
    "Maquinaria industrial", "Servicios financieros y de seguros",
    "Servicios de transporte", "Servicios recreativos, culturales y deportivos",
    "Equipos de radio, TV, comunicaciones", "Servicios agrícolas, forestales, jardinería",
    "Otros servicios comunitarios, sociales y personales", "Alimentación, bebidas, tabaco",
    "Equipos de laboratorio, óptica, precisión", "Prendas de vestir, calzado",
    "Equipos de seguridad, defensa",
}


def cargar_ya_exportados() -> set[str]:
    if YA_EXPORTADOS.exists():
        return set(json.loads(YA_EXPORTADOS.read_text()))
    return set()


def guardar_ya_exportados(ids: set[str]) -> None:
    YA_EXPORTADOS.write_text(json.dumps(sorted(ids)))


def leer_prospectos_harvey() -> list[dict]:
    if not HARVEY_DB.exists():
        print(f"No encuentro {HARVEY_DB} — ¿corriste harvey discover?", file=sys.stderr)
        return []
    conn = sqlite3.connect(f"file:{HARVEY_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT p.id as prospect_id, p.email, p.email_status, c.name as empresa, c.industry, c.location
        FROM prospects p
        JOIN companies c ON c.id = p.company_id
        WHERE p.email_status IN ('verified', 'risky') AND p.email != ''
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def extraer_ccaa(location: str) -> str:
    if not location:
        return ""
    partes = [p.strip() for p in location.split(",") if p.strip()]
    return partes[-1] if partes else ""


def obtener_stats_reales(licitaciones: list[dict], sector: str, ccaa: str) -> tuple[int, float]:
    filtradas = [t for t in licitaciones if t.get("sector") == sector and (not ccaa or t.get("ccaa") == ccaa)]
    importe_total = sum(t.get("importe") or 0 for t in filtradas)
    return len(filtradas), round(importe_total, 2)


def insertar_validacion_empresa(session: requests.Session, base_url: str, fila: dict) -> bool:
    r = session.post(f"{base_url}/rest/v1/validacion_empresas", json=fila)
    if not r.ok:
        print(f"  Fallo insertando {fila['empresa_nombre']}: {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lote-id", required=True, help="Identificador del lote, p.ej. lote-05-dataforseo-2026-10-24")
    ap.add_argument("--limite", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true", help="No escribe en Supabase ni en el CSV, solo muestra qué haría.")
    args = ap.parse_args()

    ya_exportados = cargar_ya_exportados()
    prospectos = leer_prospectos_harvey()
    nuevos = [p for p in prospectos if p["prospect_id"] not in ya_exportados][: args.limite]
    print(f"{len(prospectos)} prospectos verificados en Harvey, {len(nuevos)} nuevos para exportar.")
    if not nuevos:
        return

    print("Descargando licitaciones.json real para calcular los números del gancho...")
    resp = requests.get(LICITACIONES_JSON_URL, timeout=30)
    resp.raise_for_status()
    licitaciones = resp.json().get("licitaciones", [])
    print(f"  {len(licitaciones)} licitaciones abiertas cargadas.")

    filas_csv = []
    nuevos_ids = set()
    session, base_url = None, None
    if not args.dry_run:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            print("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY en el entorno. Usa --dry-run para probar sin ellos.", file=sys.stderr)
            sys.exit(1)
        session = requests.Session()
        session.headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"})
        base_url = url.rstrip("/")

    descartados_sin_dato = 0
    for p in nuevos:
        sector = p["industry"] if p["industry"] in SECTORES_VALIDOS else "Sin clasificar"
        ccaa = extraer_ccaa(p["location"])
        n_abiertas, importe_total = obtener_stats_reales(licitaciones, sector, ccaa)
        if sector == "Sin clasificar" or not ccaa:
            # Sin sector/ccaa reales no podemos dar un dato honesto en el
            # gancho del email — se descarta esta fila, no se inventa nada.
            descartados_sin_dato += 1
            continue

        token = secrets.token_hex(20)
        fila_db = {
            "token": token,
            "empresa_nombre": p["empresa"],
            "email_generico": p["email"],
            "sector": sector,
            "provincia": ccaa,
            "lote_id": args.lote_id,
            "fuente_contacto": "dataforseo_harvey",
        }
        if args.dry_run:
            print(f"  DRY-RUN: {p['empresa']} | {sector} | {ccaa} | {n_abiertas} abiertas, {importe_total}€")
        else:
            if not insertar_validacion_empresa(session, base_url, fila_db):
                continue

        filas_csv.append({
            "token": token,
            "empresa_nombre": p["empresa"],
            "nif": "",
            "sector": sector,
            "ccaa": ccaa,
            "n_abiertas_zona": n_abiertas,
            "importe_total_zona": importe_total,
            "lote_id": args.lote_id,
            "email_generico": p["email"],
        })
        nuevos_ids.add(p["prospect_id"])

    if descartados_sin_dato:
        print(f"{descartados_sin_dato} descartados: sector/CCAA no reconocidos, no se pudo calcular un dato real.")

    if args.dry_run:
        print(f"DRY-RUN: {len(filas_csv)} filas se habrían exportado.")
        return

    out_csv = VALIDACION_DIR / f"{args.lote_id}.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["token", "empresa_nombre", "nif", "sector", "ccaa", "n_abiertas_zona", "importe_total_zona", "lote_id", "email_generico"])
        w.writeheader()
        w.writerows(filas_csv)

    ya_exportados |= nuevos_ids
    guardar_ya_exportados(ya_exportados)
    print(f"Hecho: {len(filas_csv)} filas insertadas en validacion_empresas y escritas en {out_csv}")


if __name__ == "__main__":
    main()
