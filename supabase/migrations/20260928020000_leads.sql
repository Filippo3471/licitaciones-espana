-- Bloque 5 del prompt "copiloto de ofertas": gancho gratuito "quién gana
-- en tu sector". La tabla la escribe únicamente la Edge Function
-- capture-lead (service role) tras comprobar el consentimiento explícito
-- — nadie anónimo escribe aquí directo desde el navegador, para poder
-- validar el email y el consentimiento del lado servidor.

create table if not exists public.leads (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  sector text,
  ccaa text,
  fuente text,                      -- p.ej. 'informe_sector_gratuito'
  utm_source text,
  utm_medium text,
  utm_campaign text,
  consent_at timestamptz not null,  -- momento en que marcó la casilla, no premarcada
  baja_token uuid not null default gen_random_uuid(),
  baja_en timestamptz,
  created_at timestamptz not null default now()
);

alter table public.leads enable row level security;
-- Sin políticas de select/insert/update para anon/authenticated: solo la
-- service role (que bypassa RLS) lee y escribe, desde las Edge Functions
-- capture-lead y leads-baja.

create index if not exists leads_baja_token_idx on public.leads (baja_token);
create index if not exists leads_email_idx on public.leads (email);
