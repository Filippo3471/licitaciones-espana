// Edge Function: save-company-profile
//
// Guarda el perfil de la empresa del usuario autenticado, aplicando los
// límites de su plan (cpv_max, ccaa_max) del lado servidor — guardarlo
// directo desde el cliente a la tabla `companies` permitiría saltarse
// esos límites con una llamada REST manual. Si el usuario no tiene
// empresa todavía (alta nueva), la crea.

import { createClient } from "jsr:@supabase/supabase-js@2";
import { plans, getUserCompanyId } from "../_shared/can.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return jsonResponse({ error: "Falta autenticación" }, 401);

    const body = await req.json();
    const {
      company_name, nif, cpv_codes = [], ccaa_scope = [],
      importe_min, importe_max, facturacion_anual,
      clasificacion_empresarial, certificaciones,
    } = body;
    if (!company_name || typeof company_name !== "string") {
      return jsonResponse({ error: "El nombre de la empresa es obligatorio" }, 400);
    }

    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const companyId = await getUserCompanyId(userClient, userData.user.id);

    // Límites de plan (free si aún no hay empresa/suscripción).
    let planId = "free";
    if (companyId) {
      const { data: sub } = await adminClient
        .from("subscriptions")
        .select("plan, status")
        .eq("company_id", companyId)
        .maybeSingle();
      if (sub && (sub.status === "active" || sub.status === "trialing")) planId = sub.plan;
    }
    const limits = (plans.planes as any)[planId].limites;

    if (limits.cpv_max != null && cpv_codes.length > limits.cpv_max) {
      return jsonResponse({
        error: `Tu plan (${(plans.planes as any)[planId].nombre}) permite hasta ${limits.cpv_max} sector(es) CPV — has puesto ${cpv_codes.length}.`,
        upsell: { allowed: false, reason: "plan_feature_locked", plan: planId, limite: limits.cpv_max },
      }, 402);
    }
    if (limits.ccaa_max != null && ccaa_scope.length > limits.ccaa_max) {
      return jsonResponse({
        error: `Tu plan (${(plans.planes as any)[planId].nombre}) permite hasta ${limits.ccaa_max} comunidad(es) autónoma(s) — has puesto ${ccaa_scope.length}.`,
        upsell: { allowed: false, reason: "plan_feature_locked", plan: planId, limite: limits.ccaa_max },
      }, 402);
    }

    const row = {
      company_name, nif: nif || null, cpv_codes, ccaa_scope,
      importe_min: importe_min ?? null, importe_max: importe_max ?? null,
      facturacion_anual: facturacion_anual ?? null,
      clasificacion_empresarial: clasificacion_empresarial || null,
      certificaciones: certificaciones || null,
    };

    let finalCompanyId = companyId;
    if (!finalCompanyId) {
      const { data: newId, error: createErr } = await userClient.rpc("create_company", {
        p_company_name: row.company_name,
        p_nif: row.nif,
        p_cpv_codes: row.cpv_codes,
        p_ccaa_scope: row.ccaa_scope,
        p_importe_min: row.importe_min,
        p_importe_max: row.importe_max,
        p_facturacion_anual: row.facturacion_anual,
        p_clasificacion_empresarial: row.clasificacion_empresarial,
        p_certificaciones: row.certificaciones,
      });
      if (createErr) return jsonResponse({ error: createErr.message }, 500);
      finalCompanyId = newId;
    } else {
      const { error: updateErr } = await userClient.from("companies").update(row).eq("id", finalCompanyId);
      if (updateErr) return jsonResponse({ error: updateErr.message }, 500);
    }

    const { data: company } = await userClient.from("companies").select("*").eq("id", finalCompanyId).maybeSingle();
    return jsonResponse({ company, plan: planId });
  } catch (err) {
    return jsonResponse({ error: `Error inesperado: ${(err as Error).message}` }, 500);
  }
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "content-type": "application/json" },
  });
}
