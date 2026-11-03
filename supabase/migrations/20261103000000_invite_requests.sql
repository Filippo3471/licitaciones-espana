-- Solicitudes de acceso cuando alguien llega sin código de invitación
-- válido (o sin código). Antes el flujo era "escríbeme al Gmail
-- personal" -- esto lo sustituye por una cola que Filippo revisa por
-- lotes, sin ser el cuello de botella en tiempo real.
-- La escribe únicamente la Edge Function request-invite (service role).

create table if not exists public.invite_requests (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  empresa text,
  atendido boolean not null default false,
  atendido_en timestamptz,
  created_at timestamptz not null default now()
);

alter table public.invite_requests enable row level security;
-- Sin políticas de select/insert/update para anon/authenticated: solo la
-- service role (que bypassa RLS) escribe, desde la Edge Function
-- request-invite. Filippo lo revisa desde el dashboard de Supabase.

create index if not exists invite_requests_email_idx on public.invite_requests (email);
create index if not exists invite_requests_atendido_idx on public.invite_requests (atendido);
