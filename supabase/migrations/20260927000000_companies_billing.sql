-- Fase 1a: separa "empresa" de "usuario" (necesario para planes PRO/EQUIPO
-- con varios usuarios) y añade la infraestructura mínima de facturación.
--
-- NO destructivo: company_profiles NO se toca ni se borra en esta migración.
-- Se copian sus datos a companies/company_members y se deja la tabla vieja
-- en su sitio, sin usar, para un cleanup posterior explícito y aparte.

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
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

create table if not exists public.company_members (
  company_id uuid not null references public.companies(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'owner' check (role in ('owner', 'member')),
  created_at timestamptz not null default now(),
  primary key (company_id, user_id)
);

create table if not exists public.subscriptions (
  company_id uuid primary key references public.companies(id) on delete cascade,
  plan text not null default 'free' check (plan in ('free', 'basico', 'pro', 'equipo')),
  status text not null default 'active' check (status in ('active', 'trialing', 'past_due', 'canceled')),
  billing_interval text check (billing_interval in ('month', 'year')),
  stripe_customer_id text,
  stripe_subscription_id text,
  trial_end timestamptz,
  current_period_end timestamptz,
  coupon_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.usage_counters (
  company_id uuid not null references public.companies(id) on delete cascade,
  feature text not null,
  period text not null, -- 'YYYY-MM'
  count integer not null default 0,
  primary key (company_id, feature, period)
);

-- --- Triggers de updated_at ---
create trigger companies_set_updated_at
  before update on public.companies
  for each row execute function public.set_updated_at();

create trigger subscriptions_set_updated_at
  before update on public.subscriptions
  for each row execute function public.set_updated_at();

-- --- RLS ---
alter table public.companies enable row level security;
alter table public.company_members enable row level security;
alter table public.subscriptions enable row level security;
alter table public.usage_counters enable row level security;

create policy "select_own_company" on public.companies
  for select using (
    exists (select 1 from public.company_members m where m.company_id = companies.id and m.user_id = auth.uid())
  );
create policy "update_own_company" on public.companies
  for update using (
    exists (select 1 from public.company_members m where m.company_id = companies.id and m.user_id = auth.uid())
  );
-- Sin policy de insert directo: usar create_company() (SECURITY DEFINER) evita
-- el problema del huevo-y-gallina (no puedes ser miembro de una empresa que
-- aún no existe).

create policy "select_own_membership" on public.company_members
  for select using (
    exists (select 1 from public.company_members m2 where m2.company_id = company_members.company_id and m2.user_id = auth.uid())
  );

create policy "select_own_subscription" on public.subscriptions
  for select using (
    exists (select 1 from public.company_members m where m.company_id = subscriptions.company_id and m.user_id = auth.uid())
  );
-- Sin policy de insert/update para el cliente: solo vía service role
-- (webhooks de Stripe en la Fase 2, o create_company() para la fila inicial).

create policy "select_own_usage" on public.usage_counters
  for select using (
    exists (select 1 from public.company_members m where m.company_id = usage_counters.company_id and m.user_id = auth.uid())
  );
-- Sin policy de insert/update para el cliente: solo vía
-- increment_usage_counter() (SECURITY DEFINER) llamada desde las Edge
-- Functions con la service role key.

-- --- Funciones ---

-- Crea una empresa y hace al usuario actual su owner, en una transacción.
create or replace function public.create_company(
  p_company_name text,
  p_nif text default null,
  p_cpv_codes text[] default '{}',
  p_ccaa_scope text[] default '{}',
  p_importe_min numeric default null,
  p_importe_max numeric default null,
  p_facturacion_anual numeric default null,
  p_clasificacion_empresarial text default null,
  p_certificaciones text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_company_id uuid;
begin
  insert into public.companies (
    company_name, nif, cpv_codes, ccaa_scope, importe_min, importe_max,
    facturacion_anual, clasificacion_empresarial, certificaciones
  ) values (
    p_company_name, p_nif, p_cpv_codes, p_ccaa_scope, p_importe_min, p_importe_max,
    p_facturacion_anual, p_clasificacion_empresarial, p_certificaciones
  ) returning id into v_company_id;

  insert into public.company_members (company_id, user_id, role)
  values (v_company_id, auth.uid(), 'owner');

  insert into public.subscriptions (company_id, plan, status)
  values (v_company_id, 'free', 'active');

  return v_company_id;
end;
$$;

-- Incremento atómico de un contador de uso mensual (company_id + feature +
-- 'YYYY-MM'). Solo lo llaman las Edge Functions con la service role key.
create or replace function public.increment_usage_counter(p_company_id uuid, p_feature text, p_period text)
returns void
language sql
security definer
set search_path = public
as $$
  insert into public.usage_counters (company_id, feature, period, count)
  values (p_company_id, p_feature, p_period, 1)
  on conflict (company_id, feature, period) do update set count = usage_counters.count + 1;
$$;

-- --- Backfill: mover cada fila de company_profiles a companies +
-- company_members (owner), con su propia suscripción free. No borra ni
-- modifica company_profiles.
do $$
declare
  r record;
  v_company_id uuid;
begin
  for r in select * from public.company_profiles loop
    insert into public.companies (
      company_name, nif, cpv_codes, keywords_positive, keywords_negative, ccaa_scope,
      importe_min, importe_max, facturacion_anual, clasificacion_empresarial, certificaciones,
      created_at, updated_at
    ) values (
      r.company_name, r.nif, r.cpv_codes, r.keywords_positive, r.keywords_negative, r.ccaa_scope,
      r.importe_min, r.importe_max, r.facturacion_anual, r.clasificacion_empresarial, r.certificaciones,
      r.created_at, r.updated_at
    ) returning id into v_company_id;

    insert into public.company_members (company_id, user_id, role)
    values (v_company_id, r.user_id, 'owner');

    insert into public.subscriptions (company_id, plan, status)
    values (v_company_id, 'free', 'active');
  end loop;
end $$;
