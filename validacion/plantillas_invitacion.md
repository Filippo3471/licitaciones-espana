# Plantillas de invitación — Lote 01 (TI Madrid + Arquitectura/Ingeniería Canarias/C.Valenciana)

Estado: **DRY_RUN — no enviado.** Pendiente de tu aprobación explícita
(nº de destinatarios, sector, plantilla) antes de mandar nada, y de que
confirmes que legal ha revisado `validacion/COMPLIANCE.md`.

Variables: `{{empresa_nombre}}`, `{{n_abiertas_zona}}`,
`{{importe_total_zona}}`, `{{ccaa}}`, `{{link_entrevista}}`,
`{{link_baja}}`. El dato concreto (nº de licitaciones e importe) sale de
`validacion/desk_research.json`, no está inventado.

---

## Variante A — dato por delante

**Asunto:** {{empresa_nombre}}: {{n_abiertas_zona}} licitaciones abiertas en {{ccaa}} ahora mismo

Hola,

Soy Filippo, fundador de Licitaciones España. Os escribo porque vimos que
{{empresa_nombre}} ha sido adjudicataria de contratos públicos recientes
(dato público de PLACSP) — así que puede que esto os interese.

Ahora mismo hay **{{n_abiertas_zona}} licitaciones abiertas** en vuestro
sector en {{ccaa}}, por un importe total de **{{importe_total_zona}}€**.

Estamos investigando cómo buscan hoy licitaciones empresas como la
vuestra, antes de construir nada más. A cambio de 10 minutos en una
conversación (con un asistente de IA, no una llamada), os mandamos gratis
el informe completo y personalizado de licitaciones abiertas para vuestro
sector y zona.

👉 [Empezar (10 min)]({{link_entrevista}})

Esto es una comunicación comercial. Os escribimos porque
{{empresa_nombre}} aparece como adjudicataria en datos públicos de
contratación (PLACSP) filtrados por vuestro sector de actividad — no
tenemos ni usamos ningún otro dato vuestro.

Si no queréis recibir más mensajes como este, [daos de baja en un
clic]({{link_baja}}), sin nada que justificar.

Un saludo,
Filippo — Licitaciones España

---

## Variante B — pregunta por delante

**Asunto:** ¿Cuánto tiempo perdéis buscando licitaciones cada semana?

Hola,

Soy Filippo, fundador de Licitaciones España. Estamos hablando con
empresas de vuestro sector en {{ccaa}} para entender cómo buscáis hoy
licitaciones públicas — antes de construir nada, queremos saber si de
verdad hace falta.

Como agradecimiento por 10 minutos de conversación (con un asistente de
IA, no una llamada — os lo explicamos al entrar), os mandamos gratis un
informe con las **{{n_abiertas_zona}} licitaciones abiertas ahora mismo**
en vuestro sector en {{ccaa}} ({{importe_total_zona}}€ en total).

👉 [Empezar (10 min)]({{link_entrevista}})

Esto es una comunicación comercial. Os escribimos porque
{{empresa_nombre}} aparece como adjudicataria en datos públicos de
contratación (PLACSP) filtrados por vuestro sector de actividad — no
tenemos ni usamos ningún otro dato vuestro.

Si no queréis recibir más mensajes como este, [daos de baja en un
clic]({{link_baja}}), sin nada que justificar.

Un saludo,
Filippo — Licitaciones España

---

## Notas para la aprobación

- **Origen del contacto declarado**: adjudicación pública de contratos
  (PLACSP), filtrado por sector — cierto y verificable, no hay
  ambigüedad legal sobre "de dónde salió este email".
- **Emails**: la columna `email_generico` en `validacion/lote_01_shortlist.csv`
  está vacía todavía — antes de enviar nada hay que rellenarla con un
  email corporativo genérico real de cada empresa (no personal). Puedo
  buscarlos uno a uno (páginas de contacto públicas) en cuanto apruebes
  seguir, o me los puedes pasar tú si ya los tienes.
- **20 empresas, no 50**: recorté la shortlist a propósito a las que
  tienen un hook geográfico claro y un tamaño de contrato ganado
  compatible con pyme (excluí Accenture, Indra, Deloitte, NTT Data y
  similares que aparecían en los datos brutos — mal encaje de ICP, ya
  detectado en la Fase 1).
