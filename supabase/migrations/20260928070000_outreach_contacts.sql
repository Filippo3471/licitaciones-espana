-- Bloque 10 del prompt "copiloto de ofertas": CRM mínimo de prospección,
-- SIN enviar nada desde aquí. Solo lo escribe el script de importación
-- (validacion/import_outreach_contacts.py, con la service role key) y, a
-- futuro, el script de envío del propio Bloque 10 — nunca el frontend
-- público, así que no hace falta RLS de insert/select para anon/authenticated.
--
-- `nif` y `email` son `unique` SIN condición: en una constraint UNIQUE de
-- Postgres cada NULL cuenta como distinto de los demás (no son iguales
-- entre sí), así que varias filas sin NIF (los leads de Google Maps, que
-- no lo tienen) o sin email convive bien con la restricción.

create table if not exists public.outreach_contacts (
  id uuid primary key default gen_random_uuid(),
  empresa text not null,
  nif text unique,
  sector text,
  ccaa text,
  canal text not null default 'email' check (canal in ('email', 'linkedin', 'telefono')),
  email text unique,
  telefono text,
  web text,
  estado text not null default 'pendiente' check (estado in ('pendiente', 'contactado', 'respondio', 'llamada', 'baja')),
  fecha_contacto timestamptz,
  notas text,
  fuente text,                     -- de qué CSV/lote viene, para trazabilidad
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.outreach_contacts enable row level security;
-- Sin policies: solo accesible con la service role key (scripts locales).

create trigger outreach_contacts_set_updated_at
  before update on public.outreach_contacts
  for each row execute function public.set_updated_at();
