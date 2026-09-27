// Edge Function: create-checkout-session
//
// Crea una sesión de Stripe Checkout (modo suscripción) para que la empresa
// del usuario autenticado contrate/actualice un plan. Nunca vemos datos de
// tarjeta — Stripe los tokeniza en su propia página. El trial de 14 días de
// PRO se ofrece sin pedir tarjeta (payment_method_collection: if_required)
// y solo una vez por empresa (trial_used).

import { createClient } from "jsr:@supabase/supabase-js@2";
import Stripe from "npm:stripe@17.5.0";
import { plans, getUserCompanyId } from "../_shared/can.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const STRIPE_SECRET_KEY = Deno.env.get("STRIPE_SECRET_KEY")!;
// URL pública del frontend — a donde Stripe redirige tras éxito/cancelación.
const FRONTEND_URL = Deno.env.get("FRONTEND_URL") || "https://filippo3471.github.io/licitaciones-espana/";

const stripe = new Stripe(STRIPE_SECRET_KEY, { apiVersion: "2024-12-18.acacia" });

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

type PlanId = "basico" | "pro" | "equipo";
const PAID_PLANS: PlanId[] = ["basico", "pro", "equipo"];

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return jsonResponse({ error: "Falta autenticación" }, 401);

    const { plan, billing_interval } = await req.json();
    if (!PAID_PLANS.includes(plan)) {
      return jsonResponse({ error: `Plan inválido: ${plan}` }, 400);
    }
    if (billing_interval !== "mes" && billing_interval !== "anio") {
      return jsonResponse({ error: `Periodicidad inválida: ${billing_interval}` }, 400);
    }

    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) return jsonResponse({ error: "Sesión inválida" }, 401);

    const companyId = await getUserCompanyId(userClient, userData.user.id);
    if (!companyId) {
      return jsonResponse({ error: "Primero completa el perfil de tu empresa." }, 400);
    }

    const priceId = (plans.planes as any)[plan][
      billing_interval === "mes" ? "stripe_price_id_mes" : "stripe_price_id_anio"
    ];
    if (!priceId || priceId.startsWith("PLACEHOLDER_")) {
      return jsonResponse({ error: "Este plan todavía no tiene precio configurado en Stripe (contacta con soporte)." }, 500);
    }

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: sub } = await adminClient
      .from("subscriptions")
      .select("stripe_customer_id, trial_used")
      .eq("company_id", companyId)
      .maybeSingle();

    let customerId = sub?.stripe_customer_id as string | undefined;
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: userData.user.email,
        metadata: { company_id: companyId },
      });
      customerId = customer.id;
      await adminClient.from("subscriptions").update({ stripe_customer_id: customerId }).eq("company_id", companyId);
    }

    const wantsTrial = plan === "pro" && !sub?.trial_used;

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: customerId,
      line_items: [{ price: priceId, quantity: 1 }],
      allow_promotion_codes: true,
      success_url: `${FRONTEND_URL}?checkout=success`,
      cancel_url: `${FRONTEND_URL}?checkout=cancel`,
      payment_method_collection: wantsTrial ? "if_required" : "always",
      subscription_data: {
        metadata: { company_id: companyId, plan },
        trial_period_days: wantsTrial ? plans.trial_dias_pro : undefined,
        trial_settings: wantsTrial
          ? { end_behavior: { missing_payment_method: "cancel" } }
          : undefined,
      },
    });

    return jsonResponse({ url: session.url });
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
