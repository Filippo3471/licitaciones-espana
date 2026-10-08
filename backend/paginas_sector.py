"""Genera una página estática por sector (los de mayor volumen) con datos
reales: nº de licitaciones abiertas, importe total, desglose por CCAA y un
listado de las licitaciones con plazo más próximo. Sirve para SEO/GEO —
contenido indexable por buscadores clásicos y citable por crawlers de IA
(HTML server-rendered, sin fetch por JS) para búsquedas del tipo
"licitaciones de construcción en España".

Solo se generan páginas para sectores con suficiente volumen (>=100
licitaciones abiertas) para evitar contenido pobre/duplicado (thin content).

Uso:
    python -m backend.paginas_sector
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from .estadisticas import aviso_placsp_html

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "sector"
LICITACIONES_PATH = DATA_DIR / "licitaciones.json"
ADJUDICACIONES_PATH = DATA_DIR / "adjudicaciones.json"
SITE_BASE = "https://filippo3471.github.io/licitaciones-espana"
SUPABASE_URL = "https://fssriztfcedgmwtgkxof.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_dioPbNOINWVB3SB6X-fwJQ_YXBXrCTT"

UMBRAL_MIN_LICITACIONES = 100
IMPORTE_ATIPICO_UMBRAL = 1_000_000_000  # ver backend/estadisticas.py: acuerdos marco SDA con lotes atípicos
MAX_LICITACIONES_LISTADAS = 20
TOP_ADJUDICATARIOS = 10
TOP_ORGANOS = 10


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto


def money(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".") + "€"


def cargar_licitaciones() -> list[dict]:
    return json.loads(LICITACIONES_PATH.read_text())["licitaciones"]


def cargar_adjudicaciones() -> list[dict]:
    if not ADJUDICACIONES_PATH.exists():
        return []
    return json.loads(ADJUDICACIONES_PATH.read_text())["adjudicaciones"]


def calcular_adjudicaciones_por_sector(adjudicaciones: list[dict]) -> dict[str, dict]:
    """Gancho gratuito del Bloque 5: "quién gana en tu sector". Todo sale
    directo del histórico ya acumulado en adjudicaciones.json — ningún
    número se inventa ni se estima."""
    por_sector: dict[str, list[dict]] = defaultdict(list)
    for r in adjudicaciones:
        sector = r.get("sector")
        if sector:
            por_sector[sector].append(r)

    resultado = {}
    for sector, items in por_sector.items():
        adjudicatarios: Counter = Counter()
        importe_por_adjudicatario: dict[str, float] = defaultdict(float)
        organos: Counter = Counter()
        bajas = []
        licitadores = []
        for r in items:
            nombre = r.get("adjudicatario_nombre")
            if nombre:
                adjudicatarios[nombre] += 1
                if r.get("importe_adjudicacion"):
                    importe_por_adjudicatario[nombre] += r["importe_adjudicacion"]
            organo = r.get("organo")
            if organo:
                organos[organo] += 1
            il, ia = r.get("importe_licitacion"), r.get("importe_adjudicacion")
            if il and ia and il > 0:
                bajas.append((il - ia) / il)
            if r.get("num_licitadores") is not None:
                licitadores.append(r["num_licitadores"])

        resultado[sector] = {
            "n_adjudicaciones": len(items),
            "top_adjudicatarios": [
                {"nombre": nombre, "n_contratos": n, "importe_total": importe_por_adjudicatario.get(nombre, 0)}
                for nombre, n in adjudicatarios.most_common(TOP_ADJUDICATARIOS)
            ],
            "top_organos": organos.most_common(TOP_ORGANOS),
            "baja_media_pct": (sum(bajas) / len(bajas) * 100) if bajas else None,
            "licitadores_medio": (sum(licitadores) / len(licitadores)) if licitadores else None,
            "n_con_dato_baja": len(bajas),
            "n_con_dato_licitadores": len(licitadores),
        }
    return resultado


def calcular_por_sector(licitaciones: list[dict]) -> dict[str, dict]:
    por_sector: dict[str, list[dict]] = defaultdict(list)
    for r in licitaciones:
        sector = r.get("sector")
        if sector:
            por_sector[sector].append(r)

    resultado = {}
    for sector, items in por_sector.items():
        if len(items) < UMBRAL_MIN_LICITACIONES:
            continue

        importes_validos = [r["importe"] for r in items if r.get("importe") and r["importe"] <= IMPORTE_ATIPICO_UMBRAL]
        n_atipicas = sum(1 for r in items if r.get("importe") and r["importe"] > IMPORTE_ATIPICO_UMBRAL)
        importe_total = sum(importes_validos)

        por_ccaa: Counter = Counter()
        importe_por_ccaa: dict[str, float] = defaultdict(float)
        for r in items:
            ccaa = r.get("ccaa") or "Sin especificar"
            por_ccaa[ccaa] += 1
            if r.get("importe") and r["importe"] <= IMPORTE_ATIPICO_UMBRAL:
                importe_por_ccaa[ccaa] += r["importe"]

        proximas = sorted(
            (r for r in items if r.get("plazo_fecha")),
            key=lambda r: r["plazo_fecha"],
        )[:MAX_LICITACIONES_LISTADAS]

        resultado[sector] = {
            "n_abiertas": len(items),
            "importe_total": importe_total,
            "n_atipicas": n_atipicas,
            "por_ccaa": por_ccaa.most_common(),
            "importe_por_ccaa": importe_por_ccaa,
            "proximas": proximas,
        }
    return resultado


def render_pagina(sector: str, datos: dict, generado_en: str, adj: dict | None) -> str:
    slug = slugify(sector)
    filas_ccaa = "\n".join(
        f'<tr><td>{ccaa}</td><td class="num">{n}</td><td class="num">{money(datos["importe_por_ccaa"].get(ccaa, 0))}</td></tr>'
        for ccaa, n in datos["por_ccaa"]
    )
    filas_licitaciones = "\n".join(
        f'''<tr>
          <td><a href="{r.get("detail_url", "#")}" target="_blank" rel="noopener">{r["titulo"][:110]}</a><div class="organo">{r.get("organo", "")}</div></td>
          <td>{r.get("ccaa", "")}</td>
          <td class="num">{money(r["importe"]) if r.get("importe") else "—"}</td>
          <td>{r.get("plazo_fecha", "—")}</td>
        </tr>'''
        for r in datos["proximas"]
    )
    nota_atipicas = (
        f'<p class="nota">El importe total excluye {datos["n_atipicas"]} licitación(es) con un importe individual '
        f'superior a 1.000M€ (acuerdos marco plurianuales con lotes de valor atípico) para no distorsionar la cifra, '
        f'aunque sí cuentan en el número de licitaciones abiertas.</p>'
        if datos["n_atipicas"] else ""
    )
    titulo = f"Licitaciones públicas de {sector} en España"
    descripcion = (
        f"{datos['n_abiertas']} licitaciones públicas abiertas de {sector} en España ahora mismo, "
        f"por un importe total de {money(datos['importe_total'])}. Actualizado dos veces al día."
    )

    # Gancho gratuito (Bloque 5): quién gana en este sector, con qué baja
    # media y contra cuántos competidores — del histórico de
    # adjudicaciones ya acumulado, nunca estimado.
    seccion_ganadores = ""
    if adj and adj.get("n_adjudicaciones"):
        filas_adjudicatarios = "\n".join(
            f'<tr><td>{a["nombre"]}</td><td class="num">{a["n_contratos"]}</td><td class="num">{money(a["importe_total"])}</td></tr>'
            for a in adj["top_adjudicatarios"]
        )
        filas_organos = "\n".join(
            f'<tr><td>{organo}</td><td class="num">{n}</td></tr>'
            for organo, n in adj["top_organos"]
        )
        baja_txt = f"{adj['baja_media_pct']:.1f}%" if adj["baja_media_pct"] is not None else "sin datos suficientes"
        licitadores_txt = f"{adj['licitadores_medio']:.1f}" if adj["licitadores_medio"] is not None else "sin datos suficientes"
        seccion_ganadores = f"""
  <h2>Quién gana en este sector</h2>
  <p class="sub">De {adj['n_adjudicaciones']} adjudicaciones registradas en el histórico: baja media {baja_txt} (adjudicado frente a licitado, sobre {adj['n_con_dato_baja']} con ambos importes) · {licitadores_txt} licitadores de media por contrato (sobre {adj['n_con_dato_licitadores']} con ese dato).</p>
  <table>
    <thead><tr><th>Adjudicatario</th><th class="num">Contratos ganados</th><th class="num">Importe adjudicado</th></tr></thead>
    <tbody>
      {filas_adjudicatarios}
    </tbody>
  </table>

  <h2>Quién más contrata en este sector</h2>
  <table>
    <thead><tr><th>Órgano de contratación</th><th class="num">Adjudicaciones</th></tr></thead>
    <tbody>
      {filas_organos}
    </tbody>
  </table>
"""

    lead_form = f"""
  <div class="lead-box">
    <h2>Recibe este informe por email</h2>
    <p class="sub">Te lo mandamos cuando se actualice, con la cifra exacta de tu sector y comunidad autónoma. Nada más — puedes darte de baja en un clic en cualquier momento.</p>
    <form id="lead-form">
      <input type="email" id="lead-email" placeholder="tu@empresa.com" required>
      <input type="text" id="lead-ccaa" placeholder="Tu comunidad autónoma (opcional)">
      <input type="text" id="lead-honeypot" name="website" autocomplete="off" tabindex="-1" style="position:absolute;left:-9999px">
      <label class="lead-consent"><input type="checkbox" id="lead-consent" required> Acepto recibir este informe por email y que se guarde mi email para enviármelo. Puedo darme de baja cuando quiera.</label>
      <button type="submit" class="btn-lead">Enviarme el informe</button>
      <p class="lead-msg" id="lead-msg" role="status"></p>
    </form>
  </div>
  <script>
  (function () {{
    const SUPABASE_URL = "{SUPABASE_URL}";
    const SUPABASE_ANON_KEY = "{SUPABASE_ANON_KEY}";
    const form = document.getElementById("lead-form");
    const msg = document.getElementById("lead-msg");
    const params = new URLSearchParams(location.search);
    form.addEventListener("submit", function (e) {{
      e.preventDefault();
      msg.textContent = "Enviando…";
      fetch(SUPABASE_URL + "/functions/v1/capture-lead", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json", apikey: SUPABASE_ANON_KEY }},
        body: JSON.stringify({{
          email: document.getElementById("lead-email").value,
          sector: {json.dumps(sector)},
          ccaa: document.getElementById("lead-ccaa").value || null,
          consiente: document.getElementById("lead-consent").checked,
          honeypot: document.getElementById("lead-honeypot").value,
          fuente: "informe_sector_gratuito",
          utm_source: params.get("utm_source"),
          utm_medium: params.get("utm_medium"),
          utm_campaign: params.get("utm_campaign"),
        }}),
      }})
        .then(function (r) {{ return r.json().then(function (d) {{ return {{ ok: r.ok, d: d }}; }}); }})
        .then(function (res) {{
          msg.textContent = res.ok ? "Hecho — te lo mandaremos a ese email." : (res.d.error || "No se pudo enviar.");
          if (res.ok) form.reset();
        }})
        .catch(function () {{ msg.textContent = "No se pudo enviar. Inténtalo de nuevo."; }});
    }});
  }})();
  </script>
"""

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} | PLACSP, TED y CCAA</title>
<meta name="description" content="{descripcion}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE_BASE}/sector/{slug}.html">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{descripcion}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_BASE}/sector/{slug}.html">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{titulo}">
<meta name="twitter:description" content="{descripcion}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "{titulo}",
  "description": "{descripcion}",
  "url": "{SITE_BASE}/sector/{slug}.html",
  "temporalCoverage": "{generado_en}",
  "creator": {{"@type": "Organization", "name": "Adjuplica"}}
}}
</script>
<style>
  :root {{ --paper:#f6f5f1; --paper-raised:#fff; --ink:#1b1b18; --ink-muted:#6b6b63; --line:#e4e1d8; --accent:#1b5e4f; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  .shell {{ max-width:900px; margin:0 auto; padding:24px 16px 60px; }}
  h1 {{ font-size:1.5rem; margin:0 0 6px; }}
  h2 {{ font-size:1.1rem; margin:28px 0 10px; }}
  .sub {{ color:var(--ink-muted); font-size:0.92rem; margin:0 0 20px; }}
  a {{ color:var(--accent); }}
  table {{ width:100%; border-collapse:collapse; background:var(--paper-raised); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
  th, td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; font-size:0.86rem; vertical-align:top; }}
  th {{ background:#efece3; font-weight:600; }}
  td.num, th.num {{ text-align:right; white-space:nowrap; }}
  .organo {{ color:var(--ink-muted); font-size:0.78rem; margin-top:2px; }}
  .nota {{ font-size:0.8rem; color:var(--ink-muted); }}
  .volver {{ display:inline-block; margin-top:24px; }}
  .generado {{ font-size:0.78rem; color:var(--ink-muted); margin-top:30px; }}
  .lead-box {{ background:var(--paper-raised); border:1px solid var(--line); border-radius:8px; padding:16px; margin-top:24px; }}
  .lead-box form {{ display:flex; flex-direction:column; gap:8px; max-width:420px; }}
  .lead-box input[type=email], .lead-box input[type=text]:not(#lead-honeypot) {{ padding:8px 10px; border:1px solid var(--line); border-radius:6px; font-size:0.9rem; }}
  .lead-consent {{ font-size:0.78rem; color:var(--ink-muted); display:flex; gap:6px; align-items:flex-start; }}
  .btn-lead {{ background:var(--accent); color:#fff; border:none; border-radius:6px; padding:9px 14px; font-size:0.9rem; cursor:pointer; align-self:flex-start; }}
  .lead-msg {{ font-size:0.82rem; color:var(--ink-muted); min-height:1em; margin:0; }}
</style>
</head>
<body>
<div class="shell">
  <h1>{titulo}</h1>
  {aviso_placsp_html()}
  <p class="sub">{datos['n_abiertas']} licitaciones abiertas ahora mismo · importe total {money(datos['importe_total'])} · actualizado dos veces al día</p>

  <h2>Por comunidad autónoma</h2>
  <table>
    <thead><tr><th>Comunidad autónoma</th><th class="num">Abiertas</th><th class="num">Importe total</th></tr></thead>
    <tbody>
      {filas_ccaa}
    </tbody>
  </table>
  {nota_atipicas}
  {seccion_ganadores}
  <h2>Licitaciones con plazo más próximo</h2>
  <table>
    <thead><tr><th>Licitación</th><th>CCAA</th><th class="num">Importe</th><th>Plazo</th></tr></thead>
    <tbody>
      {filas_licitaciones}
    </tbody>
  </table>
  {lead_form}
  <a class="volver" href="../">← Buscar todas las licitaciones abiertas</a> ·
  <a class="volver" href="../estadisticas.html">Ver estadísticas completas por sector y CCAA</a>

  <p class="generado">Generado automáticamente a partir de PLACSP, TED, Generalitat de Catalunya y Ayuntamiento de Bilbao el {generado_en}.</p>
</div>
</body>
</html>
"""


def run():
    licitaciones = cargar_licitaciones()
    por_sector = calcular_por_sector(licitaciones)
    adjudicaciones_por_sector = calcular_adjudicaciones_por_sector(cargar_adjudicaciones())
    generado_en = dt.datetime.now().isoformat(timespec="seconds")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generadas = []
    slugs_vigentes = set()
    for sector, datos in por_sector.items():
        slug = slugify(sector)
        slugs_vigentes.add(slug)
        html = render_pagina(sector, datos, generado_en, adjudicaciones_por_sector.get(sector))
        (OUT_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
        generadas.append((slug, sector, datos["n_abiertas"]))

    # Borra páginas de sectores que ya no llegan al umbral de volumen —
    # si no, quedan huérfanas: sin enlaces ni en el sitemap, pero indexables.
    eliminadas = 0
    for f in OUT_DIR.glob("*.html"):
        if f.stem not in slugs_vigentes:
            f.unlink()
            eliminadas += 1
    if eliminadas:
        print(f"Eliminadas {eliminadas} páginas de sector que ya no llegan al umbral")

    print(f"Generadas {len(generadas)} páginas de sector en {OUT_DIR}")
    for slug, sector, n in sorted(generadas, key=lambda x: -x[2]):
        print(f"  {slug}.html — {sector} ({n} abiertas)")
    return generadas


if __name__ == "__main__":
    run()
