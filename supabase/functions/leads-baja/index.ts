// Edge Function: leads-baja
//
// Página de baja SIN login (Bloque 5): dado el `baja_token` que lleva el
// enlace del informe gratuito, marca ese lead como de baja. Idempotente:
// si ya estaba de baja, responde igual de bien.

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
    const { data: lead } = await adminClient.from("leads").select("id, baja_en").eq("baja_token", token).maybeSingle();
    if (!lead) return jsonResponse({ error: "Enlace de baja no válido" }, 404);

    if (!lead.baja_en) {
      await adminClient.from("leads").update({ baja_en: new Date().toISOString() }).eq("id", lead.id);
    }
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
