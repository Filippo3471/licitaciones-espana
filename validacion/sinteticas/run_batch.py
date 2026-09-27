"""Lanza las 10 entrevistas SINTÉTICAS contra la función desplegada
validacion-simular-entrevista y guarda cada transcripción por separado,
claramente etiquetada. Esto NO es validación real — sirve solo para
encontrar fallos del guion antes de hablar con ninguna empresa de verdad.

Uso:
    VALIDACION_TEST_SECRET=... python3 validacion/sinteticas/run_batch.py
"""
import concurrent.futures
import json
import os
import sys
import urllib.request
from pathlib import Path

FUNC_URL = "https://fssriztfcedgmwtgkxof.supabase.co/functions/v1/validacion-simular-entrevista"
HERE = Path(__file__).resolve().parent
TEST_SECRET = os.environ.get("VALIDACION_TEST_SECRET") or Path("/tmp/validacion_test_secret.txt").read_text().strip()
CONCURRENCIA = 4


def llamar(persona: dict) -> dict:
    body = json.dumps({
        "persona_label": persona["id"],
        "persona_system_prompt": persona["prompt"],
        "max_turns": 25,
    }).encode("utf-8")
    req = urllib.request.Request(
        FUNC_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "x-test-secret": TEST_SECRET},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    data["_etiqueta"] = "SINTÉTICA"
    data["_sector_real_asignado"] = persona["sector_real"]
    return data


def main():
    personas = json.loads((HERE / "personas.json").read_text())
    resultados = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCIA) as ex:
        futuros = {ex.submit(llamar, p): p for p in personas}
        for fut in concurrent.futures.as_completed(futuros):
            p = futuros[fut]
            try:
                data = fut.result()
                out_path = HERE / f"{p['id']}.json"
                out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                n = data.get("turnos_entrevistador")
                fin = data.get("finalizada_por_guion")
                print(f"OK  {p['id']:<45} turnos={n} finalizada_por_guion={fin}")
                resultados[p["id"]] = "ok"
            except Exception as exc:
                print(f"FALLO {p['id']:<45} {exc}")
                resultados[p["id"]] = f"error: {exc}"

    ok = sum(1 for v in resultados.values() if v == "ok")
    print(f"\n{ok}/{len(personas)} entrevistas sintéticas completadas.")


if __name__ == "__main__":
    main()
