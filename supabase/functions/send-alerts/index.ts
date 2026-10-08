// Edge Function: send-alerts (Bloque 6 — alertas reales por email)
//
// Pensada para que la invoque el cron diario (ver migración
// 20260928030000_alertas_reales.sql), no el navegador. Por cada empresa
// con una suscripción de alertas activa, mira si le toca envío según la
// frecuencia de SU PLAN (plans.json es la única fuente de verdad — no se
// lee alert_subscriptions.frecuencia para decidir el ritmo, solo para
// guardar la preferencia que el usuario marcó), filtra las licitaciones
// abiertas que encajan con sus CPV/CCAA y que no se le hayan enviado ya,
// y manda un único digest por Resend.
//
// SECRETOS NECESARIOS (no configurados todavía — sin ellos la función
// no envía nada, solo lo registra en los logs, para no fallar en silencio
// ni fingir que algo se envió cuando no es así):
//   supabase secrets set RESEND_API_KEY=re_...
//   supabase secrets set ALERTS_FROM_EMAIL="Adjuplica <alertas@tu-dominio.es>"
//
// DNS necesario en tu-dominio.es antes de que Resend entregue nada a
// bandejas de entrada normales (y no a spam): registros SPF, DKIM y DMARC
// que el propio panel de Resend te da al verificar el dominio — hay que
// añadirlos en el proveedor DNS del dominio, no aquí.

import { createClient } from "jsr:@supabase/supabase-js@2";
import { plans } from "../_shared/can.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
const ALERTS_FROM_EMAIL = Deno.env.get("ALERTS_FROM_EMAIL");
const SITE_BASE = "https://filippo3471.github.io/licitaciones-espana";
const MAX_TENDERS_POR_EMAIL = 20;

type PlanId = "free" | "basico" | "pro" | "equipo";

Deno.serve(async (_req) => {
  const resultado = { revisadas: 0, enviadas: 0, saltadas_sin_secreto: 0, errores: [] as string[] };
  try {
    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    const { data: subs } = await adminClient
      .from("alert_subscriptions")
      .select("company_id, cpv, ccaa, baja_token, last_sent_at")
      .eq("activa", true);
    if (!subs || subs.length === 0) return jsonResponse(resultado);

    const licitacionesResp = await fetch(`${SITE_BASE}/licitaciones.json`);
    if (!licitacionesResp.ok) {
      resultado.errores.push("No se pudo descargar licitaciones.json");
      return jsonResponse(resultado, 502);
    }
    const licitacionesPayload = await licitacionesResp.json();
    const licitaciones = licitacionesPayload.licitaciones as any[];
    licitacionesPayloadGeneradoEn = licitacionesPayload.generado_en;

    for (const sub of subs) {
      resultado.revisadas++;
      try {
        const { data: company } = await adminClient.from("companies").select("company_name").eq("id", sub.company_id).maybeSingle();
        const { data: subscription } = await adminClient.from("subscriptions").select("plan, status").eq("company_id", sub.company_id).maybeSingle();
        const planId: PlanId = (subscription && (subscription.status === "active" || subscription.status === "trialing")) ? (subscription.plan as PlanId) : "free";
        const alertConfig = (plans.planes as any)[planId]?.alertas ?? { frecuencia: "semanal", retraso_horas: 72 };

        const { data: members } = await adminClient.from("company_members").select("user_id").eq("company_id", sub.company_id);
        if (!members || members.length === 0) continue;
        const emails: string[] = [];
        for (const m of members) {
          const { data: userResp } = await adminClient.auth.admin.getUserById(m.user_id);
          if (userResp?.user?.email) emails.push(userResp.user.email);
        }
        if (emails.length === 0) continue;

        if (!estaDebidoHoy(alertConfig.frecuencia, sub.last_sent_at)) continue;

        const { data: yaEnviadas } = await adminClient.from("alert_sent_log").select("external_id").eq("company_id", sub.company_id);
        const enviadosSet = new Set((yaEnviadas ?? []).map((r: any) => r.external_id));

        const retrasoMs = (alertConfig.retraso_horas ?? 0) * 3600 * 1000;
        const ahora = Date.now();
        const cpv: string[] = sub.cpv ?? [];
        const ccaa: string[] = sub.ccaa ?? [];
        const candidatas = licitaciones.filter((t) => {
          if (enviadosSet.has(t.external_id)) return false;
          if (cpv.length && !(t.cpv_codes ?? []).some((c: string) => cpv.some((e) => c.startsWith(e)))) return false;
          if (ccaa.length && !ccaa.includes(t.ccaa)) return false;
          // Retraso del plan: no mandar una licitación hasta que lleve al
          // menos `retraso_horas` generada en el feed — aproximación
          // honesta (no tenemos "primera vez vista" por licitación), se
          // compara contra el momento de generación del propio JSON.
          if (retrasoMs > 0) {
            const generadoMs = Date.parse(licitacionesPayloadGeneradoEn ?? "");
            if (!Number.isNaN(generadoMs) && ahora - generadoMs < retrasoMs) return false;
          }
          return true;
        }).slice(0, MAX_TENDERS_POR_EMAIL);

        if (candidatas.length === 0) continue;

        if (!RESEND_API_KEY || !ALERTS_FROM_EMAIL) {
          resultado.saltadas_sin_secreto++;
          continue; // No se finge un envío: si falta el secreto, no se manda nada y no se marca como enviado.
        }

        const bajaUrl = `${SITE_BASE}/alerta-baja.html?t=${sub.baja_token}`;
        const html = renderDigestHtml(company?.company_name ?? "tu empresa", candidatas, bajaUrl);

        const resendResp = await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${RESEND_API_KEY}` },
          body: JSON.stringify({
            from: ALERTS_FROM_EMAIL,
            to: emails,
            subject: `${candidatas.length} licitaciones nuevas que encajan con ${company?.company_name ?? "tu empresa"}`,
            html,
          }),
        });
        if (!resendResp.ok) {
          resultado.errores.push(`Resend falló para ${sub.company_id}: ${(await resendResp.text()).slice(0, 200)}`);
          continue;
        }

        await adminClient.from("alert_sent_log").insert(candidatas.map((t) => ({ company_id: sub.company_id, external_id: t.external_id })));
        await adminClient.from("alert_subscriptions").update({ last_sent_at: new Date().toISOString() }).eq("company_id", sub.company_id);
        resultado.enviadas++;
      } catch (err) {
        resultado.errores.push(`${sub.company_id}: ${(err as Error).message}`);
      }
    }

    return jsonResponse(resultado);
  } catch (err) {
    return jsonResponse({ error: (err as Error).message, ...resultado }, 500);
  }
});

let licitacionesPayloadGeneradoEn: string | undefined;

function estaDebidoHoy(frecuencia: string, lastSentAt: string | null): boolean {
  if (!lastSentAt) return true;
  const horasDesde = (Date.now() - new Date(lastSentAt).getTime()) / 3600_000;
  if (frecuencia === "tiempo_real") return true; // el cron de verdad corre 1x/día hoy — ver nota en la migración si se quiere más frecuente
  if (frecuencia === "diaria") return horasDesde >= 20;
  return horasDesde >= 24 * 6.5; // semanal, con margen
}

function renderDigestHtml(empresa: string, tenders: any[], bajaUrl: string): string {
  const filas = tenders.map((t) => `
    <tr>
      <td style="padding:8px 0;border-bottom:1px solid #e4e1d8;">
        <a href="${t.detail_url || "#"}" style="color:#1b5e4f;text-decoration:none;font-weight:600;">${escapeHtml(t.titulo || "")}</a><br>
        <span style="color:#6b6b63;font-size:0.85em;">${escapeHtml(t.organo || "")} · ${escapeHtml(t.ccaa || "")} · plazo ${escapeHtml(t.plazo_fecha || "—")}</span>
      </td>
    </tr>`).join("");
  return `<!doctype html><html><body style="font-family:-apple-system,sans-serif;color:#1b1b18;max-width:600px;margin:0 auto;">
    <h2 style="color:#1b5e4f;">${tenders.length} licitaciones nuevas para ${escapeHtml(empresa)}</h2>
    <table style="width:100%;border-collapse:collapse;">${filas}</table>
    <p style="font-size:0.8em;color:#6b6b63;margin-top:24px;">
      Recibes esto porque tienes activas las alertas de Adjuplica para los sectores y comunidades que marcaste.
      <a href="${bajaUrl}" style="color:#1b5e4f;">Desactivar estas alertas</a>.
    </p>
  </body></html>`;
}

function escapeHtml(s: string): string {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}
