-- Fase 2: soporte Stripe. Aditivo, no toca filas existentes.
--
-- stripe_events: los webhooks de Stripe pueden reentregarse (mismo evento
-- más de una vez); guardamos el id de evento procesado para poder
-- descartar reentregas de forma idempotente sin volver a aplicar el efecto
-- (cambiar de plan, marcar impago, etc.) dos veces.
create table if not exists public.stripe_events (
  id text primary key,
  type text not null,
  processed_at timestamptz not null default now()
);

alter table public.stripe_events enable row level security;
-- Sin políticas de select/insert para el cliente: solo la Edge Function del
-- webhook (con service role, que salta RLS) escribe aquí.

-- Únicos campos que faltaban en subscriptions para el ciclo de vida Stripe
-- completo: cancel_at_period_end (saber si un cancelado sigue activo hasta
-- el final del periodo ya pagado) y trial_used (para no regalar un segundo
-- trial de 14 días gratis a la misma empresa si cancela y vuelve a probar).
alter table public.subscriptions
  add column if not exists cancel_at_period_end boolean not null default false,
  add column if not exists trial_used boolean not null default false;
