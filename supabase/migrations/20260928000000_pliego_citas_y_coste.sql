-- Bloque 2 del prompt "copiloto de ofertas": versiona el esquema del
-- resumen de pliego (para poder invalidar la caché cuando el esquema
-- cambia, sin borrar nada a mano) y añade el registro de coste real de
-- cada llamada a Anthropic, por empresa y por licitación.

alter table public.pliego_summaries
  add column if not exists schema_version integer not null default 1;

-- Los resúmenes ya cacheados antes de este cambio son del esquema 1 (sin
-- documentacion_requerida/plazos) — no se borran, pero el esquema 2 los
-- tratará como "hay que regenerar" al no coincidir la versión.

create table if not exists public.ia_usage_log (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references public.companies(id) on delete set null,
  external_id text,
  feature text not null,              -- p.ej. 'pliego_summary'
  model text,
  input_tokens integer,
  output_tokens integer,
  desde_cache boolean not null default false,  -- true = no hubo llamada real a Anthropic (coste 0)
  created_at timestamptz not null default now()
);

alter table public.ia_usage_log enable row level security;

-- Solo la propia empresa ve su historial de uso/coste; la Edge Function
-- escribe siempre con la service role key (bypassa RLS).
create policy "select_own_ia_usage" on public.ia_usage_log
  for select using (company_id is not null and public.is_company_member(company_id));

create index if not exists ia_usage_log_company_period_idx
  on public.ia_usage_log (company_id, created_at);
