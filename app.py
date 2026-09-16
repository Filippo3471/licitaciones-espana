import json

from flask import Flask, render_template, request

from backend.codelists import estado_legible, tipo_contrato_legible, tipo_organo_legible
from backend.db import get_conn
from backend.nuts_es import CCAA_POR_NUTS2

app = Flask(__name__)


def _row_to_dict(row):
    d = dict(row)
    for field in ("cpv_codes", "requisitos", "solvencia_tecnica", "solvencia_economica", "documentos"):
        d[field] = json.loads(d[field]) if d[field] else []
    d["numero"] = (d["external_id"] or "").rstrip("/").split("/")[-1]
    d["estado_legible"] = estado_legible(d["estado"])
    d["tipo_contrato_legible"] = tipo_contrato_legible(d["tipo_contrato_code"])
    d["tipo_organo_legible"] = tipo_organo_legible(d["tipo_organo_code"])
    return d


@app.route("/")
def index():
    conn = get_conn()

    estado = request.args.get("estado", "PUB")
    ccaa = request.args.get("ccaa", "")
    tipo_contrato = request.args.get("tipo_contrato", "")
    sector = request.args.get("sector", "")
    q = request.args.get("q", "").strip()

    clauses = []
    params: dict = {}
    if estado:
        clauses.append("estado = :estado")
        params["estado"] = estado
    if ccaa:
        clauses.append("ccaa = :ccaa")
        params["ccaa"] = ccaa
    if tipo_contrato:
        clauses.append("tipo_contrato_code = :tipo_contrato")
        params["tipo_contrato"] = tipo_contrato
    if sector:
        clauses.append("sector = :sector")
        params["sector"] = sector
    if q:
        clauses.append("(titulo LIKE :q OR organo LIKE :q OR objeto LIKE :q)")
        params["q"] = f"%{q}%"

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"""
        SELECT * FROM licitaciones
        {where}
        ORDER BY (plazo_fecha IS NULL), plazo_fecha ASC, updated DESC
        LIMIT 300
        """,
        params,
    ).fetchall()

    total = conn.execute("SELECT COUNT(*) c FROM licitaciones").fetchone()["c"]
    sectores = [r["sector"] for r in conn.execute("SELECT DISTINCT sector FROM licitaciones ORDER BY sector")]
    ultima_actualizacion = conn.execute(
        "SELECT MAX(fetched_at) t FROM licitaciones"
    ).fetchone()["t"]
    conn.close()

    licitaciones = [_row_to_dict(r) for r in rows]

    return render_template(
        "index.html",
        licitaciones=licitaciones,
        total=total,
        mostrando=len(licitaciones),
        sectores=sectores,
        ccaas=sorted(set(CCAA_POR_NUTS2.values())),
        filtros={"estado": estado, "ccaa": ccaa, "tipo_contrato": tipo_contrato, "sector": sector, "q": q},
        ultima_actualizacion=ultima_actualizacion,
        estado_legible_fn=estado_legible,
    )


@app.route("/licitacion/<numero>")
def detalle(numero):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM licitaciones WHERE external_id LIKE :id", {"id": f"%/{numero}"}
    ).fetchone()
    conn.close()
    if row is None:
        return render_template("detalle.html", licitacion=None), 404
    return render_template("detalle.html", licitacion=_row_to_dict(row))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
