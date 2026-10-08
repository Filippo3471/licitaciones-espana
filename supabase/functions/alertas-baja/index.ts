// Edge Function: alertas-baja
//
// Enlace de baja SIN login que lleva cada email de alertas (Bloque 6).
// Desactiva la suscripción (activa = false); no la borra, por si quiere
// reactivarla luego desde su cuenta.

import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const { token } = await req.json();
    if (!token) return jsonResponse({ error: "Falta el token de baja" }, 400);

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: sub } = await adminClient.from("alert_subscriptions").select("company_id").eq("baja_token", token).maybeSingle();
    if (!sub) return jsonResponse({ error: "Enlace de baja no válido" }, 404);

    await adminClient.from("alert_subscriptions").update({ activa: false }).eq("company_id", sub.company_id);
    return jsonResponse({ baja: true });
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
