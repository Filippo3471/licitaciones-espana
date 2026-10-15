#!/usr/bin/env python3
"""Activa los price_id reales de Stripe (modo LIVE) en plans.json,
sustituyendo los de sandbox por los de _price_ids_live_pendiente_activar.

Córrelo TÚ, desde la raíz del repo:
    python3 scripts/activar_stripe_live.py

Después:
    bash scripts/sync_plans.sh
    (y redesplegar las 9 Edge Functions que usan plans.json — ver mensaje
    de Claude con la lista exacta de comandos `supabase functions deploy`)
"""
import json
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "plans.json"

with open(RUTA, encoding="utf-8") as f:
    datos = json.load(f)

live = datos.pop("_price_ids_live_pendiente_activar")
for plan in ("basico", "pro", "equipo"):
    datos["planes"][plan]["stripe_price_id_mes"] = live[plan]["stripe_price_id_mes"]
    datos["planes"][plan]["stripe_price_id_anio"] = live[plan]["stripe_price_id_anio"]

datos["_price_ids_sandbox_test_anteriores"] = {
    "_nota": "IDs de sandbox/test que estaban activos antes del cutover a LIVE del 15-10-2026. Se guardan aquí solo como referencia/rollback, no se usan en producción.",
    "basico": {"stripe_price_id_mes": "price_1UQCP96uhjEQYWVmmC4kcamG", "stripe_price_id_anio": "price_1UQCRt6uhjEQYWVmQ2V5mjEX"},
    "pro": {"stripe_price_id_mes": "price_1UQCZd6uhjEQYWVmpiKr1Wfe", "stripe_price_id_anio": "price_1UQCag6uhjEQYWVmy9o8LFi0"},
    "equipo": {"stripe_price_id_mes": "price_1UQChT6uhjEQYWVmhLAI7yqS", "stripe_price_id_anio": "price_1UQCi36uhjEQYWVmkND5Vx4J"},
}
datos["_nota_stripe_ids"] = (
    "Los stripe_price_id de 'planes' (arriba) son los REALES de Stripe en modo LIVE, "
    "activados el 15-10-2026 — cobran dinero real. Los de sandbox/test anteriores "
    "quedan guardados en _price_ids_sandbox_test_anteriores solo como referencia."
)

with open(RUTA, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("plans.json actualizado: price_id de 'planes' ahora apuntan a Stripe LIVE.")
print("Siguiente paso: bash scripts/sync_plans.sh, y luego redesplegar las 9 Edge Functions.")
