"""Bloque 10.2 del prompt "copiloto de ofertas": genera, para cada
contacto de outreach_contacts en estado "pendiente" con sector conocido,
un mini-informe de 2-3 líneas ("quién gana en tu sector y CCAA", con los
mismos datos reales que ya usan las páginas de sector del Bloque 5) y un
enlace con UTM a la página de sector correspondiente — es lo que se
manda en el PRIMER contacto, en vez de pedir una entrevista.

NO envía nada: escribe un JSON de revisión
(validacion/outreach_mini_informes.json, gitignored) para que se repase
antes de usarse en el script de envío (Bloque 10.3).

Uso:
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_ROLE_KEY=...
    .venv/bin/python validacion/generar_mini_informes_outreach.py
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata
import re
from collections import Counter, defaultdict
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SITE_BASE = "https://filippo3471.github.io/licitaciones-espana"
IMPORTE_ATIPICO_UMBRAL = 1_000_000_000


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def money(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".") + " €"


def cargar_contactos_pendientes() -> list[dict]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY en el entorno.", file=sys.stderr)
        sys.exit(1)
    r = requests.get(
        f"{url.rstrip('/')}/rest/v1/outreach_contacts",
        params={"estado": "eq.pendiente", "sector": "not.is.null", "select": "id,empresa,nif,sector,ccaa,canal,email,telefono,web"},
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    r.raise_for_status()
    return r.json()


def calcular_stats_por_sector_ccaa(licitaciones: list[dict], adjudicaciones: list[dict]) -> dict:
    stats = defaultdict(lambda: {"n_abiertas": 0, "importe_total": 0.0})
    for r in licitaciones:
        sector = r.get("sector")
        if not sector:
            continue
        for clave in (f"{sector}|{r.get('ccaa') or ''}", f"{sector}|"):
            stats[clave]["n_abiertas"] += 1
            if r.get("importe") and r["importe"] <= IMPORTE_ATIPICO_UMBRAL:
                stats[clave]["importe_total"] += r["importe"]

    ganadores = defaultdict(Counter)
    for r in adjudicaciones:
        sector = r.get("sector")
        nombre = r.get("adjudicatario_nombre")
        if not (sector and nombre):
            continue
        for clave in (f"{sector}|{r.get('ccaa') or ''}", f"{sector}|"):
            ganadores[clave][nombre] += 1
    return stats, ganadores


def main():
    licitaciones = json.loads((RAIZ / "data/licitaciones.json").read_text())["licitaciones"]
    adjudicaciones_path = RAIZ / "data/adjudicaciones.json"
    adjudicaciones = json.loads(adjudicaciones_path.read_text())["adjudicaciones"] if adjudicaciones_path.exists() else []
    stats, ganadores = calcular_stats_por_sector_ccaa(licitaciones, adjudicaciones)

    contactos = cargar_contactos_pendientes()
    print(f"{len(contactos)} contactos pendientes con sector conocido.")

    informes = []
    sin_datos = []
    for c in contactos:
        sector = c["sector"]
        ccaa = c.get("ccaa")
        clave_zona = f"{sector}|{ccaa or ''}"
        clave_nacional = f"{sector}|"
        d = stats.get(clave_zona) if ccaa and stats.get(clave_zona, {}).get("n_abiertas") else stats.get(clave_nacional)
        zona_usada = ccaa if (ccaa and stats.get(clave_zona, {}).get("n_abiertas")) else "España"
        if not d or not d["n_abiertas"]:
            sin_datos.append(c["empresa"])
            continue

        top_ganador = None
        g = ganadores.get(clave_zona if zona_usada == ccaa else clave_nacional)
        if g:
            nombre, n = g.most_common(1)[0]
            top_ganador = {"nombre": nombre, "n_contratos": n}

        slug = slugify(sector)
        link = f"{SITE_BASE}/sector/{slug}.html?utm_source=outreach&utm_medium={c['canal']}&utm_campaign={c.get('nif') or 'google_maps'}"
        texto = (
            f"Ahora mismo hay {d['n_abiertas']} licitaciones abiertas de {sector} en {zona_usada}, "
            f"por un total de {money(d['importe_total'])}."
        )
        if top_ganador:
            texto += f" Quien más está ganando en ese sector es {top_ganador['nombre']} ({top_ganador['n_contratos']} contratos en el histórico)."
        informes.append({
            "contact_id": c["id"], "empresa": c["empresa"], "email": c.get("email"), "canal": c["canal"],
            "sector": sector, "ccaa": ccaa, "zona_usada": zona_usada, "mini_informe": texto, "link_con_utm": link,
        })

    out = RAIZ / "validacion" / "outreach_mini_informes.json"
    out.write_text(json.dumps(informes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(informes)} mini-informes escritos en {out}. {len(sin_datos)} sin datos de sector (omitidos): {sin_datos[:10]}{'…' if len(sin_datos) > 10 else ''}")


if __name__ == "__main__":
    main()
