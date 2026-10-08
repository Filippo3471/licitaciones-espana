// Edge Function: create-pliego-checkout (Bloque 8 — pago único)
//
// Crea una sesión de Stripe Checkout en modo "payment" (no suscripción)
// para comprar el análisis de UNA licitación concreta (producto_pliego_
// unico en plans.json, 9 € de PLACEHOLDER). Al completarse el pago, el
// webhook de Stripe inserta en single_tender_unlocks y ayuda-pliego deja
// pasar esa licitación aunque el plan no incluya pliego_summary.

import { createClient } from "jsr:@supabase/supabase-js@2";
import Stripe from "npm:stripe@17.5.0";
import { plans, getUserCompanyId } from "../_shared/can.ts";

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

    const { external_id, titulo } = await req.json();
    if (!external_id) return jsonResponse({ error: "Falta external_id" }, 400);

    const priceId = (plans as any).producto_pliego_unico?.stripe_price_id;
    if (!priceId || String(priceId).startsWith("PLACEHOLDER_")) {
      return jsonResponse({ error: "El análisis de un solo pliego todavía no tiene precio configurado en Stripe." }, 500);
    }

    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, { global: { headers: { Authorization: authHeader } } });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const companyId = await getUserCompanyId(userClient, userData.user.id);
    if (!companyId) return jsonResponse({ error: "Primero completa el perfil de tu empresa." }, 400);

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: yaDesbloqueado } = await adminClient.from("single_tender_unlocks").select("company_id").eq("company_id", companyId).eq("external_id", external_id).maybeSingle();
    if (yaDesbloqueado) return jsonResponse({ error: "Ya tienes acceso a esta licitación." }, 400);

    const { data: sub } = await adminClient.from("subscriptions").select("stripe_customer_id").eq("company_id", companyId).maybeSingle();
    let customerId = sub?.stripe_customer_id as string | undefined;
    if (!customerId) {
      const customer = await stripe.customers.create({ email: userData.user.email, metadata: { company_id: companyId } });
      customerId = customer.id;
      await adminClient.from("subscriptions").update({ stripe_customer_id: customerId }).eq("company_id", companyId);
    }

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      customer: customerId,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${FRONTEND_URL}?pliego_comprado=${encodeURIComponent(external_id)}`,
      cancel_url: `${FRONTEND_URL}?checkout=cancel`,
      metadata: { company_id: companyId, external_id, titulo: (titulo || "").slice(0, 400), type: "pliego_unico" },
    });

    return jsonResponse({ url: session.url });
  } catch (err) {
    return jsonResponse({ error: `Error inesperado: ${(err as Error).message}` }, 500);
  }
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS_HEADERS, "content-type": "application/json" } });
}
