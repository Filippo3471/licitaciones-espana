-- Bloque 9 del prompt "copiloto de ofertas": medición mínima del embudo,
-- sin herramientas de terceros. Solo la Edge Function track-event (y el
-- propio stripe-webhook, para "pago") escriben aquí — nadie autenticado
-- normal tiene policy de insert/select directa, así los números del
-- embudo no se pueden falsear ni leer desde el cliente.

create table if not exists public.app_events (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references public.companies(id) on delete set null,
  event_type text not null check (event_type in (
    'landing_visit', 'registro', 'primer_analisis_pliego', 'checklist_completo', 'pago'
  )),
  utm_source text,
  utm_medium text,
  utm_campaign text,
  metadata jsonb,
  created_at timestamptz not null default now()
);
alter table public.app_events enable row level security;
-- Sin policies de select/insert: solo service role (Edge Functions).

create index if not exists app_events_type_created_idx on public.app_events (event_type, created_at);
create index if not exists app_events_company_idx on public.app_events (company_id);

-- Quién puede abrir /admin.html y ver el embudo. Lo rellena a mano el
-- propio fundador desde el SQL Editor del dashboard (no hay autoalta):
--   insert into public.admin_users (user_id) values ('TU-USER-UUID');
-- (el UUID es el de auth.users, visible en Authentication → Users).
create table if not exists public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.admin_users enable row level security;
-- Sin policies: ni siquiera el propio admin lo lee por REST directo, solo
-- la Edge Function admin-stats (service role) comprueba su pertenencia.
