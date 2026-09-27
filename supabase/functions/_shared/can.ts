// Servicio único de gating: can(adminClient, companyId, feature[, opts]).
// Toda Edge Function que necesite comprobar plan/límites pasa por aquí en
// vez de reimplementar su propia lógica. Los límites y qué función
// pertenece a qué plan viven en plans.json (fuente única, ver ese archivo).
//
// IMPORTANTE: esto se llama con el cliente "adminClient" (service role),
// nunca con el cliente del usuario — la comprobación de qué empresa es la
// suya ya se hizo antes vía RLS al buscar su company_id.

import plans from "./plans.json" with { type: "json" };

type PlanId = "free" | "basico" | "pro" | "equipo";

const FEATURES_NOT_BUILT = new Set(plans.roadmap_no_construido_todavia as string[]);

export interface CanResult {
  allowed: boolean;
  reason?: "not_built" | "plan_feature_locked" | "usage_limit_reached" | "unknown_feature";
  plan: PlanId;
  message?: string;
  upgrade_to?: PlanId;
  limite?: number | null;
  usado?: number;
}

function planLimits(planId: PlanId) {
  return (plans.planes as any)[planId] ?? plans.planes.free;
}

function cheapestPlanWithFeature(feature: string): PlanId | undefined {
  const order: PlanId[] = ["free", "basico", "pro", "equipo"];
  for (const p of order) {
    if ((plans.planes as any)[p]?.funciones?.[feature]) return p;
  }
  return undefined;
}

/**
 * feature: una clave de "funciones" en plans.json (p.ej. "pliego_summary").
 * Para funciones con límite mensual de uso, pasa `usageFeatureKey` igual al
 * nombre de la clave de límite en "limites" sin el sufijo "_mes"
 * (p.ej. "pliego_summaries" para limites.pliego_summaries_mes) y este
 * módulo comprueba + puede incrementar usage_counters.
 */
export async function can(
  adminClient: any,
  companyId: string,
  feature: string,
  opts: { usageLimitKey?: string } = {}
): Promise<CanResult> {
  if (FEATURES_NOT_BUILT.has(feature)) {
    return { allowed: false, reason: "not_built", plan: "free", message: "Esta función todavía no está construida — está en el roadmap." };
  }

  const { data: sub } = await adminClient
    .from("subscriptions")
    .select("plan, status")
    .eq("company_id", companyId)
    .maybeSingle();

  const planId: PlanId = (sub && (sub.status === "active" || sub.status === "trialing")) ? (sub.plan as PlanId) : "free";
  const limits = planLimits(planId);

  const featureAllowed = !!limits.funciones?.[feature];
  if (!featureAllowed) {
    return {
      allowed: false,
      reason: "plan_feature_locked",
      plan: planId,
      upgrade_to: cheapestPlanWithFeature(feature),
      message: `Esta función no está incluida en tu plan (${limits.nombre}).`,
    };
  }

  if (opts.usageLimitKey) {
    const limitValue = limits.limites?.[`${opts.usageLimitKey}_mes`];
    if (limitValue != null) {
      const period = new Date().toISOString().slice(0, 7); // 'YYYY-MM'
      const { data: usage } = await adminClient
        .from("usage_counters")
        .select("count")
        .eq("company_id", companyId)
        .eq("feature", opts.usageLimitKey)
        .eq("period", period)
        .maybeSingle();
      const used = usage?.count ?? 0;
      if (used >= limitValue) {
        return {
          allowed: false,
          reason: "usage_limit_reached",
          plan: planId,
          upgrade_to: nextPlanWithHigherLimit(planId, opts.usageLimitKey),
          limite: limitValue,
          usado: used,
          message: `Has usado ${used}/${limitValue} este mes en tu plan ${limits.nombre}. Sube de plan para más.`,
        };
      }
    }
  }

  return { allowed: true, plan: planId };
}

function nextPlanWithHigherLimit(currentPlan: PlanId, usageKey: string): PlanId | undefined {
  const order: PlanId[] = ["free", "basico", "pro", "equipo"];
  const currentIdx = order.indexOf(currentPlan);
  const currentLimit = planLimits(currentPlan).limites?.[`${usageKey}_mes`];
  for (let i = currentIdx + 1; i < order.length; i++) {
    const l = planLimits(order[i]).limites?.[`${usageKey}_mes`];
    if (l == null || l > (currentLimit ?? 0)) return order[i];
  }
  return undefined;
}

export async function recordUsage(adminClient: any, companyId: string, usageFeatureKey: string) {
  const period = new Date().toISOString().slice(0, 7);
  await adminClient.rpc("increment_usage_counter", { p_company_id: companyId, p_feature: usageFeatureKey, p_period: period });
}

/** Busca la empresa (company_id) del usuario autenticado vía su membresía. */
export async function getUserCompanyId(userClient: any, userId: string): Promise<string | null> {
  const { data } = await userClient
    .from("company_members")
    .select("company_id")
    .eq("user_id", userId)
    .limit(1)
    .maybeSingle();
  return data?.company_id ?? null;
}

export { plans };
