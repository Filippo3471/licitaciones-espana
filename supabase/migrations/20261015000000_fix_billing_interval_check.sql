-- Bug real encontrado en la ronda de pruebas E2E de Stripe (15-10-2026):
-- subscriptions.billing_interval tenía la restricción 'month'/'year'
-- (de la migración original del 27-09-2026), pero TODO el resto del
-- código (create-checkout-session, el toggle de la landing, stripe-
-- webhook) usa "mes"/"anio" como convención. Cada vez que
-- stripe-webhook intentaba guardar una suscripción real con
-- billing_interval="mes", la restricción la rechazaba con el error
-- 23514 — y como el código no comprobaba el {error} de ese .update(),
-- fallaba en silencio: el webhook devolvía 200 a Stripe pero la fila
-- de subscriptions se quedaba en plan 'free' para siempre. Ninguna
-- suscripción de pago real se habría activado nunca en la base de
-- datos, aunque el cobro en Stripe sí hubiera funcionado.
--
-- Se alinea la restricción con la convención real de la app en vez de
-- cambiar el código en varios sitios.

alter table public.subscriptions drop constraint if exists subscriptions_billing_interval_check;
alter table public.subscriptions add constraint subscriptions_billing_interval_check
  check (billing_interval in ('mes', 'anio'));
