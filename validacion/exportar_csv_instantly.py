"""Bloque 10 (ronda 4, founder-lab): convierte los mini-informes ya
generados (validacion/outreach_mini_informes.json, Bloque 10.2) en un
CSV listo para importar como lista de leads en Instantly.ai.

NO se conecta a Instantly ni envía nada — solo escribe un CSV local
(validacion/instantly_import.csv, gitignored: contiene datos reales de
contacto). Instantly importa listas desde su panel (Leads → Import
leads → Upload CSV); las columnas personalizadas de abajo quedan
disponibles como variables {{nombre_columna}} en la secuencia.

Mapea a las dos plantillas de email (ver validacion/RUNBOOK_outreach_
instantly.md): el primer envío usa {{mini_informe}}, {{link_informe}} y
{{empresa}}; el seguimiento (paso 2) solo usa {{empresa}}.

Uso:
    .venv/bin/python validacion/exportar_csv_instantly.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "validacion" / "outreach_mini_informes.json"
SALIDA = RAIZ / "validacion" / "instantly_import.csv"


def main():
    if not ENTRADA.exists():
        print(f"No existe {ENTRADA}. Genera primero los mini-informes con "
              f"validacion/generar_mini_informes_outreach.py.", file=sys.stderr)
        sys.exit(1)

    informes = json.loads(ENTRADA.read_text(encoding="utf-8"))
    filas = [d for d in informes if d.get("email") and d.get("canal") == "email"]
    omitidos = len(informes) - len(filas)

    with SALIDA.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        # Cabeceras en el formato que espera Instantly: "email" es la
        # columna reservada; el resto son variables personalizadas.
        w.writerow(["email", "empresa", "mini_informe", "link_informe", "sector", "ccaa"])
        for d in filas:
            w.writerow([d["email"], d["empresa"], d["mini_informe"], d["link_con_utm"], d.get("sector", ""), d.get("ccaa", "")])

    print(f"{len(filas)} contactos escritos en {SALIDA} ({omitidos} omitidos: sin email o canal distinto de email).")
    print("Revisa el CSV a mano antes de subirlo — ninguna fila se ha enviado ni se enviará desde aquí.")


if __name__ == "__main__":
    main()
