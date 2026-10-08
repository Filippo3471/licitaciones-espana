// Edge Function: stripe-webhook
//
// Único punto de entrada donde Stripe nos avisa de altas, cambios de plan,
// impagos y cancelaciones. Público (Stripe no manda un JWT de Supabase) —
// la autenticidad se verifica con la firma stripe-signature + el webhook
// secret, no con verify_jwt. Desplegar con --no-verify-jwt.
//
// Idempotente: cada evento trae un id único; si ya lo procesamos
// (stripe_events), lo descartamos sin reaplicar el efecto — Stripe reintenta
// entregas y puede mandar el mismo evento más de una vez.
//
// Cancelación = soft-delete: solo cambiamos subscriptions.status, nunca
// borramos la empresa ni sus datos. can() ya trata cualquier estado que no
// sea active/trialing como plan "free" a efectos de qué funciones deja usar.

import { createClient } from "jsr:@supabase/supabase-js@2";
import Stripe from "npm:stripe@17.5.0";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const STRIPE_SECRET_KEY = Deno.env.get("STRIPE_SECRET_KEY")!;
const STRIPE_WEBHOOK_SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET")!;

const stripe = new Stripe(STRIPE_SECRET_KEY, { apiVersion: "2024-12-18.acacia" });
const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

Deno.serve(async (req) => {
  const signature = req.headers.get("stripe-signature");
  if (!signature) return new Response("Falta stripe-signature", { status: 400 });

  const body = await req.text();
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(body, signature, STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    return new Response(`Firma inválida: ${(err as Error).message}`, { status: 400 });
  }

  // Idempotencia: intenta insertar el id de evento; si ya existe (choque de
  // primary key), es una reentrega y no hay nada más que hacer.
  const { error: insertErr } = await adminClient
    .from("stripe_events")
    .insert({ id: event.id, type: event.type });
  if (insertErr) {
    return new Response("ok (evento ya procesado)", { status: 200 });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        if (session.mode === "subscription" && session.subscription) {
          const subscription = await stripe.subscriptions.retrieve(session.subscription as string);
          await syncSubscription(subscription);
        } else if (session.mode === "payment" && session.metadata?.type === "pliego_unico") {
          // Bloque 8: pago único de un solo pliego — desbloquea esa
          // licitación concreta para esa empresa, sin tocar su plan.
          const companyId = session.metadata.company_id;
          const externalId = session.metadata.external_id;
          if (companyId && externalId) {
            await adminClient.from("single_tender_unlocks").upsert({
              company_id: companyId, external_id: externalId, stripe_checkout_session_id: session.id,
            });
          }
        }
        break;
      }
      case "customer.subscription.updated":
      case "customer.subscription.created": {
        const subscription = event.data.object as Stripe.Subscription;
        await syncSubscription(subscription);
        break;
      }
      case "customer.subscription.deleted": {
        const subscription = event.data.object as Stripe.Subscription;
        const companyId = await resolveCompanyId(subscription);
        if (companyId) {
          await adminClient
            .from("subscriptions")
            .update({ status: "canceled", cancel_at_period_end: false })
            .eq("company_id", companyId);
        }
        break;
      }
      case "invoice.payment_failed": {
        const invoice = event.data.object as Stripe.Invoice;
        if (invoice.subscription) {
          const subscription = await stripe.subscriptions.retrieve(invoice.subscription as string);
          await syncSubscription(subscription);
        }
        break;
      }
      default:
        // Evento que no necesitamos manejar — ok, no es un error.
        break;
    }
    return new Response(JSON.stringify({ received: true }), { status: 200 });
  } catch (err) {
    // Si falla el procesamiento, borramos el registro de idempotencia para
    // que el reintento de Stripe pueda volver a intentarlo.
    await adminClient.from("stripe_events").delete().eq("id", event.id);
    return new Response(`Error procesando evento: ${(err as Error).message}`, { status: 500 });
  }
});

async function resolveCompanyId(subscription: Stripe.Subscription): Promise<string | null> {
  const fromMetadata = subscription.metadata?.company_id;
  if (fromMetadata) return fromMetadata;
  const { data } = await adminClient
    .from("subscriptions")
    .select("company_id")
    .eq("stripe_customer_id", subscription.customer as string)
    .maybeSingle();
  return data?.company_id ?? null;
}

async function syncSubscription(subscription: Stripe.Subscription) {
  const companyId = await resolveCompanyId(subscription);
  if (!companyId) return; // suscripción de otra cosa o metadata perdida — nada que sincronizar

  const plan = subscription.metadata?.plan ?? undefined;
  const interval = subscription.items.data[0]?.price?.recurring?.interval;
  const billingInterval = interval === "year" ? "anio" : interval === "month" ? "mes" : undefined;

  const status = mapStripeStatus(subscription.status);
  const usedTrial = subscription.status === "trialing" || !!subscription.trial_start;

  const row: Record<string, unknown> = {
    stripe_customer_id: subscription.customer as string,
    stripe_subscription_id: subscription.id,
    status,
    cancel_at_period_end: subscription.cancel_at_period_end,
    current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
  };
  if (plan) row.plan = plan;
  if (billingInterval) row.billing_interval = billingInterval;
  if (subscription.trial_end) row.trial_end = new Date(subscription.trial_end * 1000).toISOString();
  if (usedTrial) row.trial_used = true;

  await adminClient.from("subscriptions").update(row).eq("company_id", companyId);
}

function mapStripeStatus(stripeStatus: Stripe.Subscription.Status): string {
  switch (stripeStatus) {
    case "trialing":
      return "trialing";
    case "active":
      return "active";
    case "past_due":
    case "unpaid":
      return "past_due";
    case "canceled":
    case "incomplete_expired":
      return "canceled";
    default:
      return "past_due";
  }
}
