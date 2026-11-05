"""Fuente adicional: Portal de la Contratación Pública de la Comunidad de
Madrid (PCON) -- feed Atom propio, mismo esquema CODICE que PLACSP
(se reutiliza backend/parser.py tal cual, igual que placsp_agregadas.py).

El <id> de cada entrada ya es la misma URL de agregación de PLACSP
(https://agregacion.contrataciondelsectorpublico.gob.es/.../entry/<n>) que
usaría el feed agregado sindicacion_1044 -- la propia Comunidad de Madrid
dice en su web que sus licitaciones "aparecen publicadas también,
automáticamente" en PLACSP. Por eso esto NO duplica entradas: el
deduplicado final por external_id en export.py (o el upsert si algún día
se mueve a SQLite) hace que sea la MISMA fila, solo que más fresca --
este feed es en vivo, el ZIP agregado de PLACSP es mensual. El valor real
es la frescura y una red de seguridad si el ZIP mensual se retrasa o se
salta algo, no un volumen nuevo de licitaciones.

Datos abiertos: reutilización libre, sin restricciones para fines
comerciales ni no comerciales, sin clave ni límite de tasa publicado
(solo pide citar la fuente y no alterar el contenido).
https://contratos-publicos.comunidad.madrid/perfil-contratante/datos-abiertos

Verificado en vivo el 05-11-2026: ~36 páginas, formato Atom/CODICE
idéntico al feed principal de PLACSP, confirmado con curl directo.
"""
from __future__ import annotations

from .. import cpv as cpv_mod
from .. import nuts_es, parser
from ..codelists import tipo_contrato_legible
from ..fetch import iter_pages

FEED_URL = "https://contratos-publicos.comunidad.madrid/feed/licitaciones2"


def _to_float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def fetch(max_pages: int = 40) -> list[dict]:
    out = []
    try:
        for content in iter_pages(start_url=FEED_URL, max_pages=max_pages, delay=1.0):
            for row in parser.iter_entries(content):
                # Solo licitaciones abiertas (mismo criterio que _placsp_rows
                # en export.py) -- el feed de Madrid también trae entradas en
                # evaluación/adjudicadas, que no son "abiertas ahora mismo".
                if row.get("estado") != "PUB":
                    continue
                cpv = row["cpv_codes"][0] if row["cpv_codes"] else None
                out.append(
                    {
                        "fuente": "Comunidad de Madrid (PCON)",
                        "external_id": row["external_id"],
                        "expediente": row["expediente"],
                        "titulo": row["titulo"],
                        "objeto": row["objeto"],
                        "organo": row["organo"],
                        "tipo_contrato_legible": tipo_contrato_legible(row["tipo_contrato_code"]),
                        "importe": _to_float(row["importe"]),
                        "sector": cpv_mod.sector_legible(cpv) if cpv else "Sin clasificar",
                        "ccaa": nuts_es.ccaa_legible(row["ubicacion_nuts"]) or "Comunidad de Madrid",
                        "ubicacion_nombre": row["ubicacion_nombre"],
                        "estado": row["estado"],
                        "estado_legible": "Abierta (plazo de presentación en curso)",
                        "plazo_fecha": row["plazo_fecha"],
                        "plazo_hora": row["plazo_hora"],
                        "requisitos": row["requisitos"],
                        "solvencia_tecnica": row["solvencia_tecnica"],
                        "solvencia_economica": row["solvencia_economica"],
                        "documentos": row["documentos"],
                        "detail_url": row["detail_url"],
                        "cpv_codes": row["cpv_codes"],
                    }
                )
    except Exception as exc:
        print(f"[madrid] fuente no disponible ahora mismo ({exc.__class__.__name__}): se omite")
        return []
    return out
