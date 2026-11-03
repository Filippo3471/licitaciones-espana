// Edge Function pública (sin JWT): guarda una solicitud de acceso cuando
// alguien llega al registro sin código de invitación válido. Sustituye el
// flujo anterior ("escríbeme al Gmail personal de Filippo") por una cola
// que se revisa por lotes -- no bloquea a nadie esperando una respuesta
// en tiempo real, y Filippo no tiene que estar disponible al momento.

import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const body = await req.json();
    const { email, empresa, honeypot } = body ?? {};

    // Campo trampa invisible para formularios automáticos.
    if (honeypot) return jsonResponse({ ok: true });

    if (typeof email !== "string" || !EMAIL_RE.test(email.trim())) {
      return jsonResponse({ error: "Email no válido" }, 400);
    }

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { error } = await adminClient.from("invite_requests").insert({
      email: email.trim().toLowerCase(),
      empresa: typeof empresa === "string" ? empresa.trim().slice(0, 200) || null : null,
    });

    if (error) return jsonResponse({ error: error.message }, 500);
    return jsonResponse({ ok: true });
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
