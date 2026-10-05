"""Genera docs/estadisticas.html: una página de contenido real (no un
dashboard client-side) con cifras reales del propio dataset, pensada tanto
para SEO clásico como para GEO (rastreadores de IA como GPTBot/ClaudeBot no
ejecutan JavaScript, así que el contenido tiene que estar ya en el HTML,
no cargarse con fetch()).

Lee de data/licitaciones.json y data/adjudicaciones.json — el JSON ya
combinado de todas las fuentes (PLACSP + Catalunya + TED + Bilbao), no de
la base SQLite directamente, que solo contiene PLACSP y daría un recuento
incompleto.

Se ejecuta en cada refresco programado (scripts/refresh_and_publish.sh),
así las cifras nunca quedan desfasadas más de ~12 horas.

Uso:
    python3 -m backend.estadisticas
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LICITACIONES_PATH = DATA_DIR / "licitaciones.json"
ADJUDICACIONES_PATH = DATA_DIR / "adjudicaciones.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "estadisticas.html"

POCOS_LICITADORES_UMBRAL = 3
MESES_HISTORICO = 12
# Algunos sistemas dinámicos de adquisición (p.ej. Generalitat de
# Catalunya) publican cada lote como una licitación independiente pero con
# el importe del marco completo repetido en varios lotes — sumarlos sin
# más infla artificialmente el importe total de un sector. Un solo lote
# por encima de este umbral es casi con toda seguridad ese caso, así que
# se cuenta en "nº abiertas" pero se excluye de la SUMA de importe (con
# nota explícita en la página, no se oculta el porqué).
IMPORTE_ATIPICO_UMBRAL = 1_000_000_000


def calcular_estadisticas() -> dict:
    licitaciones = json.loads(LICITACIONES_PATH.read_text())["licitaciones"]
    adjudicaciones = json.loads(ADJUDICACIONES_PATH.read_text())["adjudicaciones"] if ADJUDICACIONES_PATH.exists() else []

    hoy = dt.date.today()
    desde = (hoy.replace(day=1) - dt.timedelta(days=365)).isoformat()

    por_sector: dict[str, dict] = {}

    def bucket(sector):
        return por_sector.setdefault(sector, {
            "sector": sector, "n_abiertas": 0, "importe_total": 0.0,
            "n_importes": 0, "n_adjudicadas": 0, "n_pocos": 0, "n_con_dato": 0,
        })

    n_atipicos = 0
    for it in licitaciones:
        sector = it.get("sector") or "Sin clasificar"
        b = bucket(sector)
        b["n_abiertas"] += 1
        importe = it.get("importe")
        if importe:
            if importe > IMPORTE_ATIPICO_UMBRAL:
                n_atipicos += 1
                continue
            b["importe_total"] += importe
            b["n_importes"] += 1

    for it in adjudicaciones:
        fecha = it.get("fecha_adjudicacion")
        if not fecha or fecha < desde or fecha > hoy.isoformat():
            continue
        sector = it.get("sector") or "Sin clasificar"
        b = bucket(sector)
        b["n_adjudicadas"] += 1
        n_lic = it.get("num_licitadores")
        if n_lic is not None:
            b["n_con_dato"] += 1
            if n_lic <= POCOS_LICITADORES_UMBRAL:
                b["n_pocos"] += 1

    filas = []
    for sector, b in por_sector.items():
        if b["n_abiertas"] < 5:
            continue
        filas.append({
            "sector": sector,
            "n_abiertas": b["n_abiertas"],
            "importe_total": b["importe_total"],
            "importe_medio": (b["importe_total"] / b["n_importes"]) if b["n_importes"] else None,
            "frecuencia_mensual": round(b["n_adjudicadas"] / MESES_HISTORICO, 1),
            "pct_pocos": round(100 * b["n_pocos"] / b["n_con_dato"], 1) if b["n_con_dato"] else None,
        })
    filas.sort(key=lambda x: x["importe_total"], reverse=True)

    por_ccaa: dict[str, dict] = {}
    for it in licitaciones:
        ccaa = it.get("ccaa") or "Sin especificar"
        c = por_ccaa.setdefault(ccaa, {"ccaa": ccaa, "n_abiertas": 0, "importe_total": 0.0})
        c["n_abiertas"] += 1
        importe = it.get("importe")
        if importe and importe <= IMPORTE_ATIPICO_UMBRAL:
            c["importe_total"] += importe
    filas_ccaa = sorted(por_ccaa.values(), key=lambda x: x["n_abiertas"], reverse=True)

    total_importe = sum(
        it.get("importe") or 0 for it in licitaciones
        if (it.get("importe") or 0) <= IMPORTE_ATIPICO_UMBRAL
    )

    return {
        "total_abiertas": len(licitaciones),
        "total_importe": total_importe,
        "n_atipicos_excluidos": n_atipicos,
        "por_sector": filas,
        "por_ccaa": filas_ccaa,
    }


def money(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".") + "€"



def aviso_placsp_html() -> str:
    meta = json.loads(LICITACIONES_PATH.read_text())
    if not meta.get("placsp_refresco_fallido"):
        return ""
    cuando = (meta.get("placsp_ultima_sincronizacion") or "fecha desconocida").replace("T", " ")[:16]
    return (
        '<p class="nota" style="background:#fbf3e0;border-left:4px solid #8a6a1f;padding:10px 14px;'
        'border-radius:8px;color:#1b1b18">PLACSP no ha respondido en la última actualización: sus datos son de la '
        f'sincronización completa del {cuando}. TED, Generalitat de Catalunya y Bilbao están al día.</p>'
    )


def render_html(stats: dict, generado_en: str) -> str:
    from .paginas_sector import UMBRAL_MIN_LICITACIONES, slugify

    top_sectores = stats["por_sector"][:15]
    top_ccaa = stats["por_ccaa"][:20]

    filas_sector_html = "\n".join(
        f"""<tr>
          <td>{f'<a href="sector/{slugify(s["sector"])}.html">{s["sector"]}</a>' if s['n_abiertas'] >= UMBRAL_MIN_LICITACIONES else s['sector']}</td>
          <td class="num">{s['n_abiertas']}</td>
          <td class="num">{money(s['importe_total'])}</td>
          <td class="num">{money(s['importe_medio']) if s['importe_medio'] else '—'}</td>
          <td class="num">{s['frecuencia_mensual']}</td>
          <td class="num">{f"{s['pct_pocos']}%" if s['pct_pocos'] is not None else '—'}</td>
        </tr>"""
        for s in top_sectores
    )

    filas_ccaa_html = "\n".join(
        f"""<tr>
          <td>{c['ccaa']}</td>
          <td class="num">{c['n_abiertas']}</td>
          <td class="num">{money(c['importe_total'])}</td>
        </tr>"""
        for c in top_ccaa
    )

    sector_top = top_sectores[0] if top_sectores else None
    resumen = ""
    if sector_top:
        resumen = (
            f"Ahora mismo el sector con más importe en licitaciones abiertas en España es "
            f"«{sector_top['sector']}», con {sector_top['n_abiertas']} licitaciones abiertas "
            f"por un importe total de {money(sector_top['importe_total'])}. "
        )
        alto_pocos = [s for s in top_sectores if s['pct_pocos'] and s['pct_pocos'] >= 70]
        if alto_pocos:
            ejemplo = alto_pocos[0]
            resumen += (
                f"En sectores como «{ejemplo['sector']}», el {ejemplo['pct_pocos']}% de las "
                f"adjudicaciones de los últimos 12 meses tuvieron 3 licitadores o menos, "
                f"señal de que hay hueco para más competencia."
            )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Estadísticas de licitaciones públicas en España — actualizado dos veces al día</title>
<meta name="description" content="Cuántas licitaciones públicas hay abiertas en España ahora mismo, por sector CPV y comunidad autónoma, con importes totales y medios, frecuencia de adjudicación y cuota de licitaciones con poca competencia. Datos reales de PLACSP, TED y fuentes autonómicas, actualizados dos veces al día.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://filippo3471.github.io/licitaciones-espana/estadisticas.html">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:type" content="article">
<meta property="og:title" content="Estadísticas de licitaciones públicas en España">
<meta property="og:description" content="{stats['total_abiertas']} licitaciones públicas abiertas en España ahora mismo, por sector y comunidad autónoma — datos actualizados dos veces al día.">
<meta property="og:url" content="https://filippo3471.github.io/licitaciones-espana/estadisticas.html">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "Estadísticas de licitaciones públicas abiertas en España por sector y comunidad autónoma",
  "description": "Nº de licitaciones abiertas, importe total y medio, frecuencia de adjudicación mensual y cuota de licitaciones con pocos licitadores, por sector CPV y comunidad autónoma, en España.",
  "url": "https://filippo3471.github.io/licitaciones-espana/estadisticas.html",
  "dateModified": "{generado_en}",
  "license": "https://creativecommons.org/publicdomain/zero/1.0/",
  "creator": {{"@type": "Organization", "name": "Adjuplica"}},
  "spatialCoverage": {{"@type": "Place", "name": "España"}}
}}
</script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 0 auto; padding: 24px 16px 60px; color: #1c2230; background: #eef0f2; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .sub {{ color: #5b6373; font-size: 0.9rem; margin-bottom: 20px; }}
  .resumen {{ background: #fff; border: 1px solid #d7dbe2; border-radius: 10px; padding: 18px; margin-bottom: 28px; line-height: 1.6; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; margin-bottom: 36px; font-size: 0.88rem; }}
  th, td {{ padding: 8px 10px; border-bottom: 1px solid #e4e8f6; text-align: left; }}
  th {{ background: #e4e8f6; font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.03em; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .nota {{ font-size: 0.78rem; color: #5b6373; margin-top: -20px; margin-bottom: 30px; }}
  a {{ color: #33478c; }}
  .volver {{ display: inline-block; margin-top: 20px; }}
</style>
</head>
<body>
  <h1>Estadísticas de licitaciones públicas abiertas en España</h1>
  {aviso_placsp_html()}
  <p class="sub">Datos generados el {generado_en} · fuentes: PLACSP, TED (UE), Generalitat de Catalunya, Ayuntamiento de Bilbao · se actualiza dos veces al día</p>

  <div class="resumen">
    <p><strong>Ahora mismo hay {stats['total_abiertas']} licitaciones públicas abiertas en España</strong>, por un importe total de {money(stats['total_importe'])}.</p>
    <p>{resumen}</p>
  </div>
  {f'<p class="nota">{stats["n_atipicos_excluidos"]} licitación(es) con un importe individual superior a 1.000 millones de € se excluyen de las sumas de importe (se cuentan en "nº abiertas" igualmente) — suelen ser lotes de sistemas dinámicos de adquisición que repiten el importe del marco completo en cada lote, y sumarlos daría una cifra irreal.</p>' if stats.get('n_atipicos_excluidos') else ''}

  <h2>Por sector (CPV)</h2>
  <table>
    <thead>
      <tr><th>Sector</th><th class="num">Abiertas</th><th class="num">Importe total</th><th class="num">Importe medio</th><th class="num">Adjudicaciones/mes (aprox.)</th><th class="num">% con ≤3 licitadores</th></tr>
    </thead>
    <tbody>
      {filas_sector_html}
    </tbody>
  </table>
  <p class="nota">"Adjudicaciones/mes" es una media orientativa de los últimos 12 meses de adjudicaciones registradas en el feed de PLACSP, que está sesgado hacia los meses más recientes — no es una serie histórica completa. "% con ≤3 licitadores" mide qué proporción de las adjudicaciones tuvo 3 ofertas o menos, como aproximación de baja competencia.</p>

  <h2>Por comunidad autónoma</h2>
  <table>
    <thead>
      <tr><th>Comunidad autónoma</th><th class="num">Abiertas</th><th class="num">Importe total</th></tr>
    </thead>
    <tbody>
      {filas_ccaa_html}
    </tbody>
  </table>

  <a class="volver" href="./">← Buscar licitaciones abiertas ahora</a>
</body>
</html>
"""


def run():
    stats = calcular_estadisticas()
    generado_en = dt.datetime.now().isoformat(timespec="seconds")
    html = render_html(stats, generado_en)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Generado {OUT_PATH} ({stats['total_abiertas']} licitaciones abiertas)")


if __name__ == "__main__":
    run()
