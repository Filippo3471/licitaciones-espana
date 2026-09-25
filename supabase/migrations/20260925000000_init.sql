-- Perfil de empresa por usuario, usado para GO/NO-GO y para personalizar
-- la ayuda con el pliego. Un usuario = una empresa (1:1 con auth.users).
create table if not exists public.company_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  company_name text not null,
  nif text,
  cpv_codes text[] not null default '{}',       -- divisiones CPV de interés (2 dígitos), p.ej. {'45','71'}
  keywords_positive text[] not null default '{}',
  keywords_negative text[] not null default '{}',
  ccaa_scope text[] not null default '{}',       -- comunidades autónomas de interés; vacío = toda España
  importe_min numeric,
  importe_max numeric,
  facturacion_anual numeric,
  clasificacion_empresarial text,                -- grupo/subgrupo/categoría si la tiene
  certificaciones text,                          -- texto libre: ISO 9001, ISO 14001, etc.
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.company_profiles enable row level security;

create policy "select_own_profile" on public.company_profiles
  for select using (auth.uid() = user_id);

create policy "insert_own_profile" on public.company_profiles
  for insert with check (auth.uid() = user_id);

create policy "update_own_profile" on public.company_profiles
  for update using (auth.uid() = user_id);

create policy "delete_own_profile" on public.company_profiles
  for delete using (auth.uid() = user_id);

-- Mantiene updated_at al día en cada UPDATE.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger company_profiles_set_updated_at
  before update on public.company_profiles
  for each row execute function public.set_updated_at();

-- Caché de resúmenes de pliego: es sobre la LICITACIÓN, no sobre la
-- empresa, así que se comparte entre todos los usuarios que la consulten.
-- Solo la Edge Function (con la service role key) escribe aquí.
create table if not exists public.pliego_summaries (
  external_id text primary key,       -- mismo external_id que en licitaciones.json
  fuente text,
  document_hash text,                 -- hash del/de los PDF procesados, para detectar cambios
  resumen jsonb not null,             -- ver estructura documentada en supabase/functions/ayuda-pliego
  model text,                         -- qué modelo lo generó, para trazabilidad
  created_at timestamptz not null default now()
);

alter table public.pliego_summaries enable row level security;

-- Cualquier usuario autenticado puede leer resúmenes (son sobre datos
-- públicos de la licitación, no sobre ninguna empresa).
create policy "select_summaries_authenticated" on public.pliego_summaries
  for select using (auth.role() = 'authenticated');

-- Nadie escribe directamente desde el cliente: solo la Edge Function,
-- que usa la service role key y por tanto no pasa por RLS.
