// Edge Function: capture-lead
//
// Guarda un lead del formulario "Recibe este informe de tu sector" (gancho
// gratuito del Bloque 5). El consentimiento NUNCA se asume: si `consiente`
// no es explícitamente `true`, se rechaza la petición — no se guarda nada.
// No hace falta sesión: este formulario vive en páginas estáticas públicas
// (docs/sector/*.html), antes de que exista ninguna cuenta.

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
    const { email, sector, ccaa, consiente, fuente, utm_source, utm_medium, utm_campaign, honeypot } = body ?? {};

    // Campo trampa invisible para formularios automáticos: si viene
    // relleno, es un bot — se responde OK sin guardar nada, para no darle
    // pistas de que fue detectado.
    if (honeypot) return jsonResponse({ ok: true });

    if (typeof email !== "string" || !EMAIL_RE.test(email.trim())) {
      return jsonResponse({ error: "Email no válido" }, 400);
    }
    if (consiente !== true) {
      return jsonResponse({ error: "Falta marcar la casilla de consentimiento" }, 400);
    }

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data, error } = await adminClient
      .from("leads")
      .insert({
        email: email.trim().toLowerCase(),
        sector: sector || null,
        ccaa: ccaa || null,
        fuente: fuente || "informe_sector_gratuito",
        utm_source: utm_source || null,
        utm_medium: utm_medium || null,
        utm_campaign: utm_campaign || null,
        consent_at: new Date().toISOString(),
      })
      .select("id")
      .single();

    if (error) return jsonResponse({ error: error.message }, 500);
    return jsonResponse({ ok: true, id: data.id });
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
