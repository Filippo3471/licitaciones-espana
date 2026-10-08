-- Bloque 7 del prompt "copiloto de ofertas": modo consultora. Una cuenta
-- (la que paga, `companies`) puede gestionar varias EMPRESAS CLIENTE,
-- cada una con su propio perfil de solvencia, sin que cada cliente
-- necesite su propia suscripción — la suscripción sigue siendo 1:1 con
-- `companies` (no se toca `subscriptions` ni su RLS), esto es aditivo.
--
-- Gating: cuántas empresas cliente puede tener una cuenta lo decide
-- plans.json → limites.empresas_max del plan de `companies` (null =
-- ilimitadas, como en Equipo). Lo aplica la Edge Function
-- save-client-company, no una CHECK de SQL, porque el límite vive en
-- plans.json (fuente única), no en la base de datos.

create table if not exists public.client_companies (
  id uuid primary key default gen_random_uuid(),
  managed_by_company_id uuid not null references public.companies(id) on delete cascade,
  company_name text not null,
  nif text,
  cpv_codes text[] not null default '{}',
  keywords_positive text[] not null default '{}',
  keywords_negative text[] not null default '{}',
  ccaa_scope text[] not null default '{}',
  importe_min numeric,
  importe_max numeric,
  facturacion_anual numeric,
  clasificacion_empresarial text,
  certificaciones text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.client_companies enable row level security;

create policy "select_own_client_companies" on public.client_companies
  for select using (public.is_company_member(managed_by_company_id));
create policy "insert_own_client_companies" on public.client_companies
  for insert with check (public.is_company_member(managed_by_company_id));
create policy "update_own_client_companies" on public.client_companies
  for update using (public.is_company_member(managed_by_company_id));
create policy "delete_own_client_companies" on public.client_companies
  for delete using (public.is_company_member(managed_by_company_id));

create trigger client_companies_set_updated_at
  before update on public.client_companies
  for each row execute function public.set_updated_at();

-- El checklist se guarda POR EMPRESA CLIENTE cuando aplica, en vez de
-- forzar una columna nullable dentro de la clave primaria de
-- offer_checklists (Postgres exige NOT NULL en toda columna de una
-- primary key, así que no se puede meter ahí "sin cliente" = NULL). Dos
-- ofertas del mismo expediente para dos clientes distintos de una
-- consultora no comparten checklist entre sí ni con el de la propia
-- cuenta.
create table if not exists public.client_offer_checklists (
  client_company_id uuid not null references public.client_companies(id) on delete cascade,
  external_id text not null,
  items jsonb not null default '[]',
  updated_at timestamptz not null default now(),
  primary key (client_company_id, external_id)
);

alter table public.client_offer_checklists enable row level security;

create policy "select_client_checklist" on public.client_offer_checklists
  for select using (exists (
    select 1 from public.client_companies c
    where c.id = client_offer_checklists.client_company_id and public.is_company_member(c.managed_by_company_id)
  ));
create policy "insert_client_checklist" on public.client_offer_checklists
  for insert with check (exists (
    select 1 from public.client_companies c
    where c.id = client_offer_checklists.client_company_id and public.is_company_member(c.managed_by_company_id)
  ));
create policy "update_client_checklist" on public.client_offer_checklists
  for update using (exists (
    select 1 from public.client_companies c
    where c.id = client_offer_checklists.client_company_id and public.is_company_member(c.managed_by_company_id)
  ));

create trigger client_offer_checklists_set_updated_at
  before update on public.client_offer_checklists
  for each row execute function public.set_updated_at();

-- El registro de coste de IA sí admite NULL aquí sin problema: no forma
-- parte de ninguna clave, solo se usa para desglosar coste por cliente.
alter table public.ia_usage_log
  add column if not exists client_company_id uuid references public.client_companies(id) on delete set null;
