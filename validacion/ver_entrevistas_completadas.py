"""Lista las entrevistas de validación completadas (o cortadas por límite de
tiempo/turnos), con la empresa, el email y el transcript — para que puedas
escribir tú mismo un seguimiento personal a cada una (la parte "unscalable"
del plan, ver conversación del 25-10-2026).

No envía nada — solo lee de Supabase.

Requiere:
    export SUPABASE_URL=https://fssriztfcedgmwtgkxof.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=...

Uso:
    .venv/bin/python validacion/ver_entrevistas_completadas.py
    .venv/bin/python validacion/ver_entrevistas_completadas.py --desde 2026-10-27
"""
from __future__ import annotations

import argparse
import os
import sys

import requests


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", help="Solo entrevistas finalizadas desde esta fecha (YYYY-MM-DD).")
    args = ap.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Faltan SUPABASE_URL y/o SUPABASE_SERVICE_ROLE_KEY en el entorno.", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"apikey": key, "Authorization": f"Bearer {key}"})
    base = url.rstrip("/")

    params = {
        "select": "*",
        "estado": "in.(completa,parcial_limite_alcanzado)",
        "order": "finalizada_en.desc",
    }
    if args.desde:
        params["finalizada_en"] = f"gte.{args.desde}"

    r = session.get(f"{base}/rest/v1/validacion_entrevistas", params=params)
    r.raise_for_status()
    entrevistas = r.json()

    if not entrevistas:
        print("Ninguna entrevista completada todavía.")
        return

    tokens = list({e["empresa_token"] for e in entrevistas})
    r2 = session.get(
        f"{base}/rest/v1/validacion_empresas",
        params={"select": "token,empresa_nombre,email_generico,sector,provincia", "token": f"in.({','.join(tokens)})"},
    )
    r2.raise_for_status()
    empresas = {e["token"]: e for e in r2.json()}

    print(f"{len(entrevistas)} entrevista(s) completada(s):\n")
    for e in entrevistas:
        emp = empresas.get(e["empresa_token"], {})
        print("=" * 70)
        print(f"Empresa: {emp.get('empresa_nombre', '?')}  |  Email: {emp.get('email_generico', '?')}")
        print(f"Sector: {emp.get('sector', '?')}  |  Zona: {emp.get('provincia', '?')}")
        print(f"Estado: {e['estado']}  |  Terminada: {e.get('finalizada_en', '?')}")
        print("-" * 70)
        for turno in e.get("transcript") or []:
            quien = "IA" if turno["hablante"] == "entrevistador" else "ELLOS"
            print(f"[{quien}] {turno['texto']}")
        print()


if __name__ == "__main__":
    main()
