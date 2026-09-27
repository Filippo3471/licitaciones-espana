-- Fase 3 de validación (Prompt 4): tablas para el entrevistador de
-- producción. Aditivo, no toca ninguna tabla del MVP. RLS activada sin
-- ninguna política para anon/authenticated — solo la Edge Function del
-- entrevistador (con service role) lee y escribe aquí. No hay acceso
-- público a estos datos en ningún caso.

-- Empresas invitadas: aquí SÍ puede vivir el nombre de la empresa y un
-- email de contacto (necesarios para invitar y para la preventa), pero
-- nunca el nombre de una persona concreta ni datos personales más allá de
-- un email de empresa genérico.
create table if not exists public.validacion_empresas (
  token text primary key,                    -- token no adivinable, va en la URL de invitación
  empresa_nombre text not null,
  email_generico text,
  sector text not null,
  provincia text,
  tamaño_estimado text,                       -- p.ej. "1-10", "11-50", "51-250"
  dato_gancho text,                           -- el dato concreto usado en la invitación (para trazabilidad del embudo)
  lote_id text not null,
  estado_invitacion text not null default 'preparada'
    check (estado_invitacion in ('preparada', 'dry_run', 'enviada', 'abierta', 'iniciada', 'completada', 'rebotada', 'baja')),
  fuente_contacto text,                       -- de dónde se obtuvo el contacto (para poder decírselo si preguntan)
  creado_en timestamptz not null default now(),
  invitada_en timestamptz,
  baja_en timestamptz
);

-- La tabla de ANÁLISIS real. Nunca contiene el nombre de una persona ni el
-- nombre de la empresa directamente — solo los metadatos agregables
-- (sector, provincia, tamaño) que pide el Prompt 4. Se relaciona con
-- validacion_empresas por el token, pero el análisis (Fase 5) debe operar
-- sobre esta tabla sin necesitar unir con la de empresas.
create table if not exists public.validacion_entrevistas (
  id uuid primary key default gen_random_uuid(),
  empresa_token text references public.validacion_empresas(token),
  es_sintetica boolean not null default false,
  sector text not null,
  provincia text,
  tamaño_estimado text,
  estado text not null default 'en_curso'
    check (estado in ('en_curso', 'completa', 'parcial_abandonada', 'parcial_limite_alcanzado')),
  transcript jsonb not null default '[]'::jsonb,
  turnos_entrevistador int not null default 0,
  reaccion_informe_puntuacion int check (reaccion_informe_puntuacion between 1 and 5),
  reaccion_informe_texto text,
  preventa_ofrecida boolean not null default false,
  preventa_aceptada boolean not null default false,
  preventa_email_contacto text,
  consentimiento_en timestamptz,
  iniciada_en timestamptz not null default now(),
  finalizada_en timestamptz
);

create index if not exists idx_validacion_entrevistas_sector on public.validacion_entrevistas(sector);
create index if not exists idx_validacion_entrevistas_estado on public.validacion_entrevistas(estado);

alter table public.validacion_empresas enable row level security;
alter table public.validacion_entrevistas enable row level security;
-- Sin políticas: ni anon ni authenticated pueden leer ni escribir estas
-- tablas directamente. Todo pasa por la Edge Function con service role.
