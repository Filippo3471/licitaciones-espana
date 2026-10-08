// Edge Function: admin-stats (Bloque 9 — página interna /admin.html)
//
// Solo responde si el usuario autenticado está en admin_users (sin
// autoalta — se añade a mano desde el SQL Editor, ver la migración
// 20260928060000_medicion.sql). Devuelve el embudo semanal (Bloque 9.1)
// y el coste real de IA por pliego (Bloque 2.5), nunca cifras inventadas:
// todo sale de app_events / ia_usage_log.

import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const SEMANAS_A_MOSTRAR = 8;
// Precio orientativo de claude-sonnet-5 por token — ajústalo si cambia tu
// tarifa real; se usa solo para dar una cifra de coste aproximada, nunca
// para facturar nada.
const COSTE_INPUT_POR_1M = 3; // USD por millón de tokens de entrada
const COSTE_OUTPUT_POR_1M = 15; // USD por millón de tokens de salida

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return jsonResponse({ error: "Falta autenticación" }, 401);

    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, { global: { headers: { Authorization: authHeader } } });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: isAdmin } = await adminClient.from("admin_users").select("user_id").eq("user_id", userData.user.id).maybeSingle();
    if (!isAdmin) return jsonResponse({ error: "No tienes acceso a esta página." }, 403);

    const desde = new Date();
    desde.setDate(desde.getDate() - SEMANAS_A_MOSTRAR * 7);

    const { data: eventos } = await adminClient
      .from("app_events")
      .select("event_type, company_id, created_at, utm_source")
      .gte("created_at", desde.toISOString());

    const semanas = construirSemanas(SEMANAS_A_MOSTRAR);
    const embudo = semanas.map((inicioSemana, idx) => {
      const finSemana = idx + 1 < semanas.length ? semanas[idx + 1] : new Date();
      const enSemana = (tipo: string) => (eventos ?? []).filter((e) => e.event_type === tipo && new Date(e.created_at) >= inicioSemana && new Date(e.created_at) < finSemana).length;
      const companiesConAnalisis = new Set((eventos ?? []).filter((e) => e.event_type === "primer_analisis_pliego" && new Date(e.created_at) >= inicioSemana && new Date(e.created_at) < finSemana && e.company_id).map((e) => e.company_id));
      return {
        semana_inicio: inicioSemana.toISOString().slice(0, 10),
        landing_visit: enSemana("landing_visit"),
        registro: enSemana("registro"),
        primer_analisis_pliego: enSemana("primer_analisis_pliego"),
        empresas_con_analisis: companiesConAnalisis.size,
        checklist_completo: enSemana("checklist_completo"),
        pago: enSemana("pago"),
      };
    });

    const porFuente: Record<string, number> = {};
    for (const e of eventos ?? []) {
      if (e.event_type !== "landing_visit") continue;
      const fuente = e.utm_source || "(directo)";
      porFuente[fuente] = (porFuente[fuente] ?? 0) + 1;
    }

    const { data: usage } = await adminClient
      .from("ia_usage_log")
      .select("input_tokens, output_tokens, desde_cache, external_id")
      .gte("created_at", desde.toISOString());

    const generaciones = (usage ?? []).filter((u) => !u.desde_cache);
    const totalInput = generaciones.reduce((s, u) => s + (u.input_tokens || 0), 0);
    const totalOutput = generaciones.reduce((s, u) => s + (u.output_tokens || 0), 0);
    const costeTotalUsd = (totalInput / 1_000_000) * COSTE_INPUT_POR_1M + (totalOutput / 1_000_000) * COSTE_OUTPUT_POR_1M;
    const costePorPliegoUsd = generaciones.length ? costeTotalUsd / generaciones.length : null;

    return jsonResponse({
      embudo,
      visitas_por_fuente: porFuente,
      coste_ia: {
        periodo_dias: SEMANAS_A_MOSTRAR * 7,
        generaciones_nuevas: generaciones.length,
        lecturas_desde_cache: (usage ?? []).length - generaciones.length,
        total_input_tokens: totalInput,
        total_output_tokens: totalOutput,
        coste_total_usd_aprox: Math.round(costeTotalUsd * 100) / 100,
        coste_por_pliego_usd_aprox: costePorPliegoUsd != null ? Math.round(costePorPliegoUsd * 1000) / 1000 : null,
        nota: `Estimado con ${COSTE_INPUT_POR_1M} USD/M tokens entrada y ${COSTE_OUTPUT_POR_1M} USD/M salida — ajusta estas tarifas en el código si cambian; nunca sustituye tu factura real de Anthropic.`,
      },
    });
  } catch (err) {
    return jsonResponse({ error: `Error inesperado: ${(err as Error).message}` }, 500);
  }
});

function construirSemanas(n: number): Date[] {
  const semanas: Date[] = [];
  const hoy = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(hoy);
    d.setDate(d.getDate() - i * 7);
    d.setHours(0, 0, 0, 0);
    semanas.push(d);
  }
  return semanas;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS_HEADERS, "content-type": "application/json" } });
}
