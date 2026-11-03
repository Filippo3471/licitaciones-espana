// Edge Function pública (sin JWT): procesa una solicitud de acceso cuando
// alguien llega al registro sin código de invitación válido.
//
// Cupo semanal real (no falso): si quedan plazas en los últimos 7 días
// (INVITE_WEEKLY_CAP, por defecto 10), se concede el código al instante en
// la propia respuesta -- cero espera, cero intervención de Filippo. Si el
// cupo de la semana ya está lleno, la solicitud queda en cola
// (invite_requests, atendido=false) para la siguiente tanda. El cupo es
// real -- cuenta solicitudes reales de los últimos 7 días -- no decorativo.
//
// Requiere: supabase secrets set SIGNUP_INVITE_CODE=<código>
// Opcional: supabase secrets set INVITE_WEEKLY_CAP=10

import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SIGNUP_INVITE_CODE = Deno.env.get("SIGNUP_INVITE_CODE");
const WEEKLY_CAP = Number(Deno.env.get("INVITE_WEEKLY_CAP") || "10");

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
    const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
    const { count, error: countError } = await adminClient
      .from("invite_requests")
      .select("id", { count: "exact", head: true })
      .gte("created_at", since);

    if (countError) return jsonResponse({ error: countError.message }, 500);

    const hayHueco = (count ?? 0) < WEEKLY_CAP && !!SIGNUP_INVITE_CODE;

    const { error: insertError } = await adminClient.from("invite_requests").insert({
      email: email.trim().toLowerCase(),
      empresa: typeof empresa === "string" ? empresa.trim().slice(0, 200) || null : null,
      atendido: hayHueco,
      atendido_en: hayHueco ? new Date().toISOString() : null,
    });

    if (insertError) return jsonResponse({ error: insertError.message }, 500);

    return jsonResponse(hayHueco ? { ok: true, codigo: SIGNUP_INVITE_CODE } : { ok: true });
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
