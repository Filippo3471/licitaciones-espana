-- Bloque 4 del prompt "copiloto de ofertas": checklist marcable de
-- documentos + plazos por licitación analizada, por empresa. El propio
-- navegador (vía supabase-js con RLS, igual que companies/subscriptions)
-- lee y escribe esta tabla directamente — no hace falta una Edge Function.

create table if not exists public.offer_checklists (
  company_id uuid not null references public.companies(id) on delete cascade,
  external_id text not null,
  items jsonb not null default '[]',   -- [{key, label, done}]
  updated_at timestamptz not null default now(),
  primary key (company_id, external_id)
);

alter table public.offer_checklists enable row level security;

create policy "select_own_checklist" on public.offer_checklists
  for select using (public.is_company_member(company_id));

create policy "insert_own_checklist" on public.offer_checklists
  for insert with check (public.is_company_member(company_id));

create policy "update_own_checklist" on public.offer_checklists
  for update using (public.is_company_member(company_id));

create trigger offer_checklists_set_updated_at
  before update on public.offer_checklists
  for each row execute function public.set_updated_at();
