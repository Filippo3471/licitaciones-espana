-- Arregla el cron de alertas reales (Bloque 6 / migración 20260928030000):
-- 1) pg_cron y pg_net no estaban habilitadas, así que el cron.schedule()
--    original nunca llegó a crear el job (el `if exists(...)` lo saltó en
--    silencio) — esta migración lo vuelve a intentar, ahora que deberían
--    estar activadas.
-- 2) El enfoque original pedía `alter database postgres set app.settings...`
--    para pasarle la URL y el service_role_key al cron job — pero en un
--    proyecto gestionado de Supabase ni el dashboard tiene permiso para
--    eso (ERROR 42501: permission denied to set parameter), verificado en
--    vivo el 15-10-2026. Se sustituye por Supabase Vault (sí tiene permiso
--    desde el SQL Editor): la URL no es secreta así que va literal, y el
--    service_role_key se guarda cifrado en vault y se lee con
--    vault.decrypted_secrets en el momento de cada ejecución del cron.

do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron')
     and exists (select 1 from pg_extension where extname = 'pg_net') then

    -- Quita el job antiguo si llegó a crearse alguna vez (no debería,
    -- pero por si acaso, para no duplicar el envío diario).
    if exists (select 1 from cron.job where jobname = 'adjuplica-send-alerts-daily') then
      perform cron.unschedule('adjuplica-send-alerts-daily');
    end if;

    perform cron.schedule(
      'adjuplica-send-alerts-daily',
      '0 7 * * *',  -- 07:00 UTC ≈ 08:00/09:00 España, antes del refresco de datos de las 09:00
      $cron$
        select net.http_post(
          url := 'https://fssriztfcedgmwtgkxof.supabase.co/functions/v1/send-alerts',
          headers := jsonb_build_object(
            'Authorization', 'Bearer ' || (
              select decrypted_secret from vault.decrypted_secrets
              where name = 'service_role_key' limit 1
            ),
            'Content-Type', 'application/json'
          ),
          body := '{}'::jsonb
        );
      $cron$
    );
  end if;
end $$;

-- Falta un último paso manual, que no se puede meter en una migración
-- porque el valor es secreto (el service_role_key no debe quedar en el
-- repo): guardarlo en Vault, UNA vez, desde el SQL Editor del dashboard:
--
--   select vault.create_secret('TU_SERVICE_ROLE_KEY', 'service_role_key');
--
-- (si ya existe un secreto con ese nombre de un intento anterior, usa
-- vault.update_secret en su lugar — el propio INSERT fallará con un
-- aviso claro de duplicado si hace falta).
