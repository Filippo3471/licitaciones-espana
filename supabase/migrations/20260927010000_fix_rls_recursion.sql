-- Las políticas de company_members/companies/subscriptions/usage_counters
-- comprobaban pertenencia haciendo un subselect directo sobre
-- company_members desde dentro de la propia política de company_members
-- — Postgres lo detecta como recursión infinita y rechaza la consulta
-- entera (error 42P17), dejando esas tablas ilegibles para cualquier
-- usuario normal. Solo cambia metadata de políticas, no toca datos.

create or replace function public.is_company_member(p_company_id uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.company_members
    where company_id = p_company_id and user_id = auth.uid()
  );
$$;

drop policy if exists "select_own_company" on public.companies;
create policy "select_own_company" on public.companies
  for select using (public.is_company_member(companies.id));

drop policy if exists "update_own_company" on public.companies;
create policy "update_own_company" on public.companies
  for update using (public.is_company_member(companies.id));

drop policy if exists "select_own_membership" on public.company_members;
create policy "select_own_membership" on public.company_members
  for select using (public.is_company_member(company_members.company_id));

drop policy if exists "select_own_subscription" on public.subscriptions;
create policy "select_own_subscription" on public.subscriptions
  for select using (public.is_company_member(subscriptions.company_id));

drop policy if exists "select_own_usage" on public.usage_counters;
create policy "select_own_usage" on public.usage_counters
  for select using (public.is_company_member(usage_counters.company_id));
