"""Genera docs/sitemap.xml completo: la portada, la página de estadísticas y
todas las páginas de sector generadas por backend.paginas_sector. Se
regenera en cada ciclo porque el conjunto de sectores que cruza el umbral
de volumen (ver UMBRAL_MIN_LICITACIONES) puede cambiar de un día a otro.

Uso:
    python -m backend.sitemap
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .paginas_sector import calcular_por_sector, cargar_licitaciones, slugify

SITE_BASE = "https://filippo3471.github.io/licitaciones-espana"
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "sitemap.xml"


def _url(loc: str, priority: str, changefreq: str = "daily") -> str:
    hoy = dt.date.today().isoformat()
    return (
        f"  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{hoy}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"  </url>"
    )


def run():
    licitaciones = cargar_licitaciones()
    por_sector = calcular_por_sector(licitaciones)

    urls = [
        _url(f"{SITE_BASE}/", "1.0"),
        _url(f"{SITE_BASE}/estadisticas.html", "0.9"),
    ]
    for sector in sorted(por_sector, key=lambda s: -por_sector[s]["n_abiertas"]):
        slug = slugify(sector)
        urls.append(_url(f"{SITE_BASE}/sector/{slug}.html", "0.8"))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    OUT_PATH.write_text(xml, encoding="utf-8")
    print(f"Generado {OUT_PATH} ({len(urls)} URLs)")


if __name__ == "__main__":
    run()
