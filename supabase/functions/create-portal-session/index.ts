// Edge Function: create-portal-session
//
// Abre el Customer Portal de Stripe para que la empresa gestione su método
// de pago, vea facturas, o cancele. La cancelación real la procesa Stripe;
// nosotros solo reaccionamos al webhook customer.subscription.deleted.

import { createClient } from "jsr:@supabase/supabase-js@2";
import Stripe from "npm:stripe@17.5.0";
import { getUserCompanyId } from "../_shared/can.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const STRIPE_SECRET_KEY = Deno.env.get("STRIPE_SECRET_KEY")!;
const FRONTEND_URL = Deno.env.get("FRONTEND_URL") || "https://filippo3471.github.io/licitaciones-espana/";

const stripe = new Stripe(STRIPE_SECRET_KEY, { apiVersion: "2024-12-18.acacia" });

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return jsonResponse({ error: "Falta autenticación" }, 401);

    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const companyId = await getUserCompanyId(userClient, userData.user.id);
    if (!companyId) return jsonResponse({ error: "No se encontró tu empresa." }, 400);

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: sub } = await adminClient
      .from("subscriptions")
      .select("stripe_customer_id")
      .eq("company_id", companyId)
      .maybeSingle();

    if (!sub?.stripe_customer_id) {
      return jsonResponse({ error: "Todavía no tienes una suscripción de pago activa." }, 400);
    }

    const portalSession = await stripe.billingPortal.sessions.create({
      customer: sub.stripe_customer_id,
      return_url: FRONTEND_URL,
    });

    return jsonResponse({ url: portalSession.url });
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
