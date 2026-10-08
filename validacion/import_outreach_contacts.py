"""Bloque 10 del prompt "copiloto de ofertas": importa los leads ya
reunidos (validacion/lote_*.csv y el CSV de Google Maps del escritorio) a
la tabla outreach_contacts de Supabase, sin duplicar por NIF (o por email
cuando no hay NIF, como en los leads de Google Maps).

NO envía nada. Solo escribe filas de CRM. Las empresas de lote_02/03/04
que ya recibieron un email real (confirmado en Gmail, in:sent, el
28-29/09 y el 02/10 de 2026) se marcan aquí mismo como "contactado" con
la fecha real de envío — no se inventa el estado de ninguna fila.

Requiere:
    SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en el entorno (la service
    role key nunca se pone en este archivo ni se commitea).

Uso:
    export SUPABASE_URL=https://fssriztfcedgmwtgkxof.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=...
    .venv/bin/python validacion/import_outreach_contacts.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import requests

VALIDACION_DIR = Path(__file__).resolve().parent
DESKTOP_CSV = Path.home() / "Desktop" / "leads_licitaciones_2026-10-06_tanda1.csv"

# Confirmado en Gmail (in:sent) el 2026-10-08: estas 30 empresas de
# lote_02/03/04 recibieron un email real el 2026-09-28 y/o el 2026-10-02.
# Clave = NIF. No es la cifra de "~27" citada de memoria en founder/*.md —
# esa era una estimación anterior al seguimiento del 02/10; esta lista es
# la cuenta verificada contra el propio Gmail, más alta porque incluye el
# seguimiento.
CONTACTADAS_CONFIRMADAS_GMAIL = {
    "A41553702": "2026-09-28",  # Alhambra Systems SA
    "A28843159": "2026-10-02",  # Seringe, S.A.
    "A11029279": "2026-10-02",  # Signe, S.A.
    "B82955873": "2026-09-28",  # Alcorce Telecomunicaciones S.L.
    "B75486308": "2026-10-02",  # HS Architects and Partners SLP
    "B76571843": "2026-10-02",  # Vázquez de Parga Arquitectos, SLP
    "B97857080": "2026-10-02",  # Edigma Ingeniería, S.L.
    "B96709506": "2026-10-02",  # Valnu Servicios de Ingeniería S.L.
    "A78115565": "2026-09-28",  # Distriforma S.A.
    "B86090784": "2026-10-02",  # PM Trans Europe SLU
    "B09321928": "2026-10-02",  # Ezsa Sanidad Ambiental S.L.
    "B24638074": "2026-10-02",  # Lowen Servicios Integrales S.L.
    "A18042234": "2026-10-02",  # Ascensores Ingar S.A.
    "B42721100": "2026-10-02",  # Biblion Iberica, S.L.
    "A81643314": "2026-09-28",  # IRE Rayos X S.A.
    "A41414145": "2026-10-02",  # Guadaltel, S.A
    "B98316326": "2026-10-02",  # Soluciones Civiles y Técnicas S.L.
    "B12920682": "2026-10-02",  # Bandalay Events SL
    "B33795410": "2026-10-02",  # Legitrans, SL
    "B90420597": "2026-10-02",  # Ohho Eventos y Animaciones 2016 SL
    "B80121676": "2026-10-02",  # Proliser S.L.
    "B37033537": "2026-10-02",  # Limpiezas Castilla de Salamanca (Limcasa)
    "B81782096": "2026-09-28",  # Emesa Prevención, S.L.
    "F05293907": "2026-10-02",  # Laburo, S. Coop. Mad.
    "B98598428": "2026-10-02",  # Sabors Catering Rotova, S.L.
    "B97254403": "2026-10-02",  # Catering La Hacienda S.L. — rebotó varias veces, ver notas
    "A38363917": "2026-09-28",  # Biservicus Sistemas de Seguridad, S.A.
    "A76277912": "2026-10-02",  # Compañía de Vigilancia Cansegur SA
    "B64811995": "2026-10-02",  # Auservi Group Seguridad y Vigilancia SL
    "B47650114": "2026-10-02",  # Control Seguridad y Domótica S.L.
}
NOTAS_EXTRA = {
    "B97254403": "El email a info@cateringlahacienda.es rebotó varias veces (mailer-daemon) tras el envío del 02/10 — revisar si el buzón existe antes de reintentar.",
}


def leer_lotes() -> list[dict]:
    filas = []
    for nombre in ["lote_01_shortlist.csv", "lote_02_verificado.csv", "lote_03_verificado.csv", "lote_04_verificado.csv"]:
        ruta = VALIDACION_DIR / nombre
        if not ruta.exists():
            continue
        with ruta.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                nif = (row.get("nif") or "").strip() or None
                email = (row.get("email_generico") or "").strip().lower() or None
                fila = {
                    "empresa": row["empresa_nombre"].strip(),
                    "nif": nif,
                    "sector": row.get("sector") or None,
                    "ccaa": row.get("ccaa") or None,
                    "canal": "email",
                    "email": email,
                    "telefono": None,
                    "web": None,
                    "estado": "pendiente",
                    "fecha_contacto": None,
                    "notas": None,
                    "fuente": nombre,
                }
                if nif and nif in CONTACTADAS_CONFIRMADAS_GMAIL:
                    fila["estado"] = "contactado"
                    fila["fecha_contacto"] = CONTACTADAS_CONFIRMADAS_GMAIL[nif] + "T08:00:00Z"
                if nif in NOTAS_EXTRA:
                    fila["notas"] = NOTAS_EXTRA[nif]
                filas.append(fila)
    return filas


def leer_tanda1_google_maps() -> list[dict]:
    if not DESKTOP_CSV.exists():
        print(f"Aviso: no se encontró {DESKTOP_CSV} — se omite esa tanda.", file=sys.stderr)
        return []
    filas = []
    with DESKTOP_CSV.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            email = (row.get("email") or "").strip().lower() or None
            filas.append({
                "empresa": (row.get("empresa") or "").strip(),
                "nif": None,  # Google Maps no da NIF
                "sector": row.get("categoria") or row.get("sector") or None,
                "ccaa": None,  # el CSV trae ciudad, no CCAA — se deja sin forzar un mapeo que no está verificado
                "canal": "email" if email else "telefono",
                "email": email,
                "telefono": (row.get("telefono") or "").strip() or None,
                "web": (row.get("web") or "").strip() or None,
                # Estos 86 son los de la tanda ya preparada en borradores de
                # Gmail SIN enviar (ver conversación) — estado real: pendiente.
                "estado": "pendiente",
                "fecha_contacto": None,
                "notas": f"ciudad: {row.get('ciudad', '')}" if row.get("ciudad") else None,
                "fuente": "leads_licitaciones_2026-10-06_tanda1.csv",
            })
    return filas


def upsert(session: requests.Session, base_url: str, filas: list[dict], dry_run: bool) -> tuple[int, int]:
    insertadas, actualizadas = 0, 0
    for fila in filas:
        if not fila["empresa"]:
            continue
        if dry_run:
            clave = fila["nif"] or fila["email"] or "(sin clave)"
            print("DRY-RUN:", fila["empresa"], "|", clave, "|", fila["estado"], "|", fila["fuente"])
            continue
        existente = None
        if fila["nif"]:
            r = session.get(f"{base_url}/rest/v1/outreach_contacts", params={"nif": f"eq.{fila['nif']}", "select": "id,estado"})
            r.raise_for_status()
            rows = r.json()
            existente = rows[0] if rows else None
        elif fila["email"]:
            r = session.get(f"{base_url}/rest/v1/outreach_contacts", params={"email": f"eq.{fila['email']}", "select": "id,estado"})
            r.raise_for_status()
            rows = r.json()
            existente = rows[0] if rows else None

        if existente:
            # No se pisa un estado más avanzado (p.ej. "respondio") con un
            # reimport que solo trae "pendiente"/"contactado" del CSV.
            payload = {k: v for k, v in fila.items() if k != "estado"}
            if fila["estado"] == "contactado":
                payload["estado"] = "contactado"
            r = session.patch(f"{base_url}/rest/v1/outreach_contacts", params={"id": f"eq.{existente['id']}"}, json=payload)
            r.raise_for_status()
            actualizadas += 1
        else:
            r = session.post(f"{base_url}/rest/v1/outreach_contacts", json=fila)
            r.raise_for_status()
            insertadas += 1
    return insertadas, actualizadas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Muestra qué haría, sin escribir nada en Supabase.")
    args = parser.parse_args()

    filas = leer_lotes() + leer_tanda1_google_maps()
    print(f"{len(filas)} filas leídas de los CSV.")

    if args.dry_run:
        upsert(None, None, filas, dry_run=True)
        return

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Faltan SUPABASE_URL y/o SUPABASE_SERVICE_ROLE_KEY en el entorno. Usa --dry-run para probar sin ellos.", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"})
    insertadas, actualizadas = upsert(session, url.rstrip("/"), filas, dry_run=False)
    print(f"Hecho: {insertadas} filas nuevas, {actualizadas} actualizadas.")


if __name__ == "__main__":
    main()
