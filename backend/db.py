import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "licitaciones.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS licitaciones (
    external_id TEXT PRIMARY KEY,
    expediente TEXT,
    detail_url TEXT,
    updated TEXT,
    estado TEXT,
    titulo TEXT,
    objeto TEXT,
    organo TEXT,
    tipo_organo_code TEXT,
    tipo_contrato_code TEXT,
    importe REAL,
    cpv_codes TEXT,
    sector TEXT,
    ubicacion_nombre TEXT,
    ubicacion_nuts TEXT,
    ccaa TEXT,
    plazo_fecha TEXT,
    plazo_hora TEXT,
    requisitos TEXT,
    solvencia_tecnica TEXT,
    solvencia_economica TEXT,
    documentos TEXT,
    pyme_adjudicado TEXT,
    fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_estado ON licitaciones(estado);
CREATE INDEX IF NOT EXISTS idx_ccaa ON licitaciones(ccaa);
CREATE INDEX IF NOT EXISTS idx_plazo ON licitaciones(plazo_fecha);
"""

# Columnas añadidas después de la primera versión del esquema: se agregan
# con ALTER TABLE (idempotente) en vez de romper las bases de datos que ya
# existen en disco de usuarios que actualizan el código.
EXTRA_COLUMNS = {
    "fecha_adjudicacion": "TEXT",
    "importe_adjudicacion": "REAL",
    "num_licitadores": "INTEGER",
    "num_pymes_licitadoras": "INTEGER",
    "adjudicatario_nombre": "TEXT",
    "adjudicatario_nif": "TEXT",
    "adjudicatario_ciudad": "TEXT",
    "adjudicatario_ccaa": "TEXT",
}


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(licitaciones)")}
    for col, coltype in EXTRA_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE licitaciones ADD COLUMN {col} {coltype}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fecha_adj ON licitaciones(fecha_adjudicacion)")
    conn.commit()
    return conn


def upsert(conn, row: dict, sector: str, ccaa: str, fetched_at: str):
    def as_float(v):
        try:
            return float(v) if v is not None else None
        except ValueError:
            return None

    def as_int(v):
        try:
            return int(v) if v is not None else None
        except ValueError:
            return None

    from .nuts_es import ccaa_legible

    conn.execute(
        """
        INSERT INTO licitaciones (
            external_id, expediente, detail_url, updated, estado, titulo, objeto,
            organo, tipo_organo_code, tipo_contrato_code, importe, cpv_codes, sector,
            ubicacion_nombre, ubicacion_nuts, ccaa, plazo_fecha, plazo_hora,
            requisitos, solvencia_tecnica, solvencia_economica, documentos,
            pyme_adjudicado, fetched_at,
            fecha_adjudicacion, importe_adjudicacion, num_licitadores, num_pymes_licitadoras,
            adjudicatario_nombre, adjudicatario_nif, adjudicatario_ciudad, adjudicatario_ccaa
        ) VALUES (
            :external_id, :expediente, :detail_url, :updated, :estado, :titulo, :objeto,
            :organo, :tipo_organo_code, :tipo_contrato_code, :importe, :cpv_codes, :sector,
            :ubicacion_nombre, :ubicacion_nuts, :ccaa, :plazo_fecha, :plazo_hora,
            :requisitos, :solvencia_tecnica, :solvencia_economica, :documentos,
            :pyme_adjudicado, :fetched_at,
            :fecha_adjudicacion, :importe_adjudicacion, :num_licitadores, :num_pymes_licitadoras,
            :adjudicatario_nombre, :adjudicatario_nif, :adjudicatario_ciudad, :adjudicatario_ccaa
        )
        ON CONFLICT(external_id) DO UPDATE SET
            expediente=excluded.expediente,
            detail_url=excluded.detail_url,
            updated=excluded.updated,
            estado=excluded.estado,
            titulo=excluded.titulo,
            objeto=excluded.objeto,
            organo=excluded.organo,
            tipo_organo_code=excluded.tipo_organo_code,
            tipo_contrato_code=excluded.tipo_contrato_code,
            importe=excluded.importe,
            cpv_codes=excluded.cpv_codes,
            sector=excluded.sector,
            ubicacion_nombre=excluded.ubicacion_nombre,
            ubicacion_nuts=excluded.ubicacion_nuts,
            ccaa=excluded.ccaa,
            plazo_fecha=excluded.plazo_fecha,
            plazo_hora=excluded.plazo_hora,
            requisitos=excluded.requisitos,
            solvencia_tecnica=excluded.solvencia_tecnica,
            solvencia_economica=excluded.solvencia_economica,
            documentos=excluded.documentos,
            pyme_adjudicado=excluded.pyme_adjudicado,
            fetched_at=excluded.fetched_at,
            fecha_adjudicacion=excluded.fecha_adjudicacion,
            importe_adjudicacion=excluded.importe_adjudicacion,
            num_licitadores=excluded.num_licitadores,
            num_pymes_licitadoras=excluded.num_pymes_licitadoras,
            adjudicatario_nombre=excluded.adjudicatario_nombre,
            adjudicatario_nif=excluded.adjudicatario_nif,
            adjudicatario_ciudad=excluded.adjudicatario_ciudad,
            adjudicatario_ccaa=excluded.adjudicatario_ccaa
        WHERE excluded.updated IS NOT NULL AND (
            licitaciones.updated IS NULL OR excluded.updated >= licitaciones.updated
        )
        """,
        {
            **row,
            "importe": as_float(row.get("importe")),
            "cpv_codes": json.dumps(row.get("cpv_codes") or [], ensure_ascii=False),
            "sector": sector,
            "ccaa": ccaa,
            "requisitos": json.dumps(row.get("requisitos") or [], ensure_ascii=False),
            "solvencia_tecnica": json.dumps(row.get("solvencia_tecnica") or [], ensure_ascii=False),
            "solvencia_economica": json.dumps(row.get("solvencia_economica") or [], ensure_ascii=False),
            "documentos": json.dumps(row.get("documentos") or [], ensure_ascii=False),
            "fetched_at": fetched_at,
            "fecha_adjudicacion": row.get("fecha_adjudicacion"),
            "importe_adjudicacion": as_float(row.get("importe_adjudicacion")),
            "num_licitadores": as_int(row.get("num_licitadores")),
            "num_pymes_licitadoras": as_int(row.get("num_pymes_licitadoras")),
            "adjudicatario_nombre": row.get("adjudicatario_nombre"),
            "adjudicatario_nif": row.get("adjudicatario_nif"),
            "adjudicatario_ciudad": row.get("adjudicatario_ciudad"),
            "adjudicatario_ccaa": ccaa_legible(row.get("adjudicatario_ccaa_nuts")) if row.get("adjudicatario_ccaa_nuts") else None,
        },
    )
