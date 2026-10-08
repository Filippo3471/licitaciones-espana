// Edge Function: track-event (Bloque 9 — medición mínima del embudo)
//
// Registra uno de los 5 eventos mínimos del embudo. Pública (una visita a
// la landing todavía no tiene sesión), pero sin Authorization intenta
// igual resolver company_id si hay un JWT válido en la cabecera — para
// eventos de usuario ya logueado (registro, análisis, checklist).
// "pago" lo escribe directamente stripe-webhook, no esta función.

import { createClient } from "jsr:@supabase/supabase-js@2";
import { getUserCompanyId } from "../_shared/can.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const EVENTOS_VALIDOS = new Set(["landing_visit", "registro", "primer_analisis_pliego", "checklist_completo"]);

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const { event_type, utm_source, utm_medium, utm_campaign, metadata } = await req.json();
    if (!EVENTOS_VALIDOS.has(event_type)) return jsonResponse({ error: "event_type no válido" }, 400);

    let companyId: string | null = null;
    const authHeader = req.headers.get("Authorization");
    if (authHeader) {
      try {
        const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, { global: { headers: { Authorization: authHeader } } });
        const { data: userData } = await userClient.auth.getUser();
        if (userData?.user) companyId = await getUserCompanyId(userClient, userData.user.id);
      } catch { /* evento anónimo si el token no es válido */ }
    }

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    await adminClient.from("app_events").insert({
      company_id: companyId, event_type,
      utm_source: utm_source || null, utm_medium: utm_medium || null, utm_campaign: utm_campaign || null,
      metadata: metadata ?? null,
    });
    return jsonResponse({ ok: true });
  } catch (err) {
    return jsonResponse({ error: `Error inesperado: ${(err as Error).message}` }, 500);
  }
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS_HEADERS, "content-type": "application/json" } });
}
