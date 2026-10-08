-- Bloque 8 del prompt "copiloto de ofertas": pago único "Análisis de 1
-- pliego" (9 €, ver plans.json → producto_pliego_unico) para quien licita
-- poco y no quiere una suscripción. Lo escribe únicamente el webhook de
-- Stripe (service role) al confirmar el pago — nunca el cliente directo.

create table if not exists public.single_tender_unlocks (
  company_id uuid not null references public.companies(id) on delete cascade,
  external_id text not null,
  stripe_checkout_session_id text,
  unlocked_at timestamptz not null default now(),
  primary key (company_id, external_id)
);

alter table public.single_tender_unlocks enable row level security;

create policy "select_own_unlocks" on public.single_tender_unlocks
  for select using (public.is_company_member(company_id));
