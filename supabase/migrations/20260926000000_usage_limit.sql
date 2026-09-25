-- Uso diario de "Ayuda con el pliego" por usuario, para limitar el coste
-- real (cada análisis nuevo llama a la API de Anthropic). Solo cuenta
-- análisis NUEVOS (no los servidos desde la caché de pliego_summaries),
-- que es lo único que cuesta dinero.
create table if not exists public.pliego_usage (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null default current_date,
  count integer not null default 0,
  primary key (user_id, day)
);

alter table public.pliego_usage enable row level security;

create policy "select_own_usage" on public.pliego_usage
  for select using (auth.uid() = user_id);

-- Solo la Edge Function (service role) escribe aquí; sin política de
-- insert/update para el cliente.

-- Incremento atómico (upsert + suma) para evitar condiciones de carrera
-- si un usuario dispara dos análisis casi a la vez. SECURITY DEFINER para
-- que funcione aunque se llame vía el cliente "de usuario" en el futuro,
-- pero hoy solo la Edge Function (service role) la invoca.
create or replace function public.increment_pliego_usage(p_user_id uuid, p_day date)
returns void
language sql
security definer
set search_path = public
as $$
  insert into public.pliego_usage (user_id, day, count)
  values (p_user_id, p_day, 1)
  on conflict (user_id, day) do update set count = pliego_usage.count + 1;
$$;
