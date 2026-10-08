-- Bloque 6 del prompt "copiloto de ofertas": alertas reales por email.
-- HOY esto NO envía nada de verdad todavía — falta configurar el secreto
-- RESEND_API_KEY y el dominio verificado (ver README de la Edge Function
-- send-alerts). El cron queda programado pero la función no hace nada
-- real mientras falte ese secreto, así que activar esto no tiene efecto
-- hasta que se complete la configuración manual.

create table if not exists public.alert_subscriptions (
  company_id uuid primary key references public.companies(id) on delete cascade,
  cpv text[] not null default '{}',
  ccaa text[] not null default '{}',
  frecuencia text not null default 'semanal' check (frecuencia in ('semanal', 'diaria', 'tiempo_real')),
  activa boolean not null default true,
  baja_token uuid not null default gen_random_uuid(),  -- enlace de baja en cada email, sin necesidad de login
  last_sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.alert_subscriptions enable row level security;

create policy "select_own_alert_sub" on public.alert_subscriptions
  for select using (public.is_company_member(company_id));
create policy "insert_own_alert_sub" on public.alert_subscriptions
  for insert with check (public.is_company_member(company_id));
create policy "update_own_alert_sub" on public.alert_subscriptions
  for update using (public.is_company_member(company_id));

create trigger alert_subscriptions_set_updated_at
  before update on public.alert_subscriptions
  for each row execute function public.set_updated_at();

-- Para no repetir la misma licitación en dos envíos — solo la Edge
-- Function (service role) la toca.
create table if not exists public.alert_sent_log (
  company_id uuid not null references public.companies(id) on delete cascade,
  external_id text not null,
  sent_at timestamptz not null default now(),
  primary key (company_id, external_id)
);
alter table public.alert_sent_log enable row level security;
create policy "select_own_alert_sent_log" on public.alert_sent_log
  for select using (public.is_company_member(company_id));

-- --- Cron: dispara send-alerts una vez al día. La propia función decide,
-- para cada suscripción, si hoy le toca según su frecuencia y el retraso
-- de su plan (plans.json) — este cron solo marca "es un buen momento para
-- mirar", no envía nada por sí mismo.
--
-- pg_cron y pg_net deben estar habilitados en el proyecto (Database →
-- Extensions en el dashboard de Supabase, o `create extension` si tienes
-- permiso). Si no están disponibles, esta parte de la migración falla
-- sola sin tocar el resto de tablas — aplícala a mano después de activar
-- las extensiones si falla aquí.
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron')
     and exists (select 1 from pg_extension where extname = 'pg_net') then
    perform cron.schedule(
      'adjuplica-send-alerts-daily',
      '0 7 * * *',  -- 07:00 UTC ≈ 08:00/09:00 España, antes del refresco de datos de las 09:00
      $cron$
        select net.http_post(
          url := current_setting('app.settings.supabase_url', true) || '/functions/v1/send-alerts',
          headers := jsonb_build_object(
            'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key', true),
            'Content-Type', 'application/json'
          ),
          body := '{}'::jsonb
        );
      $cron$
    );
  end if;
end $$;

-- `app.settings.supabase_url` y `app.settings.service_role_key` no existen
-- por defecto — hay que fijarlos una vez con (sustituye los valores):
--   alter database postgres set app.settings.supabase_url = 'https://TU-PROYECTO.supabase.co';
--   alter database postgres set app.settings.service_role_key = 'TU_SERVICE_ROLE_KEY';
-- (ejecútalo en el SQL Editor del dashboard, con permisos de superusuario
-- del proyecto; no se puede meter en una migración porque el service role
-- key no debe quedar en el repo).
