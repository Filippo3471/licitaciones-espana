// Edge Function: save-client-company (Bloque 7 — modo consultora)
//
// Crea, actualiza o borra una EMPRESA CLIENTE gestionada por la cuenta
// (companies) del usuario autenticado. Aplica del lado servidor el gating
// de plan: la función "multi_empresa" tiene que estar en el plan (Equipo,
// hoy) y el número de empresas cliente no puede superar
// limites.empresas_max — igual que save-company-profile hace con
// cpv_max/ccaa_max, por el mismo motivo: si solo se comprobara en el
// cliente, cualquiera podría saltárselo con una llamada REST directa.

import { createClient } from "jsr:@supabase/supabase-js@2";
import { can, getUserCompanyId } from "../_shared/can.ts";

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

    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, { global: { headers: { Authorization: authHeader } } });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const companyId = await getUserCompanyId(userClient, userData.user.id);
    if (!companyId) return jsonResponse({ error: "No se encontró tu empresa. Completa primero tu perfil." }, 400);

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const veredicto = await can(adminClient, companyId, "multi_empresa");
    if (!veredicto.allowed) return jsonResponse({ error: veredicto.message, upsell: veredicto }, 402);

    const body = await req.json();
    const accion = body.accion as "crear" | "actualizar" | "borrar";

    if (accion === "borrar") {
      if (!body.id) return jsonResponse({ error: "Falta id" }, 400);
      const { error } = await adminClient.from("client_companies").delete().eq("id", body.id).eq("managed_by_company_id", companyId);
      if (error) return jsonResponse({ error: error.message }, 500);
      return jsonResponse({ ok: true });
    }

    const { company_name, nif, cpv_codes = [], ccaa_scope = [], importe_min, importe_max, facturacion_anual, clasificacion_empresarial, certificaciones } = body;
    if (!company_name || typeof company_name !== "string") {
      return jsonResponse({ error: "El nombre de la empresa cliente es obligatorio" }, 400);
    }

    if (accion === "crear") {
      const { count } = await adminClient.from("client_companies").select("id", { count: "exact", head: true }).eq("managed_by_company_id", companyId);
      const { plans } = await import("../_shared/can.ts");
      const empresasMax = (plans.planes as any)[veredicto.plan]?.limites?.empresas_max;
      if (empresasMax != null && (count ?? 0) >= empresasMax) {
        return jsonResponse({ error: `Tu plan (${(plans.planes as any)[veredicto.plan].nombre}) permite hasta ${empresasMax} empresa(s) cliente.`, upsell: { allowed: false, reason: "usage_limit_reached", plan: veredicto.plan, limite: empresasMax } }, 402);
      }
      const { data, error } = await adminClient.from("client_companies").insert({
        managed_by_company_id: companyId, company_name, nif: nif || null, cpv_codes, ccaa_scope,
        importe_min: importe_min ?? null, importe_max: importe_max ?? null, facturacion_anual: facturacion_anual ?? null,
        clasificacion_empresarial: clasificacion_empresarial || null, certificaciones: certificaciones || null,
      }).select("*").single();
      if (error) return jsonResponse({ error: error.message }, 500);
      return jsonResponse({ ok: true, client_company: data });
    }

    if (accion === "actualizar") {
      if (!body.id) return jsonResponse({ error: "Falta id" }, 400);
      const { data, error } = await adminClient.from("client_companies").update({
        company_name, nif: nif || null, cpv_codes, ccaa_scope,
        importe_min: importe_min ?? null, importe_max: importe_max ?? null, facturacion_anual: facturacion_anual ?? null,
        clasificacion_empresarial: clasificacion_empresarial || null, certificaciones: certificaciones || null,
      }).eq("id", body.id).eq("managed_by_company_id", companyId).select("*").single();
      if (error) return jsonResponse({ error: error.message }, 500);
      return jsonResponse({ ok: true, client_company: data });
    }

    return jsonResponse({ error: "accion debe ser 'crear', 'actualizar' o 'borrar'" }, 400);
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
