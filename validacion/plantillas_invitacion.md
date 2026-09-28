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
- **`validacion/lote_01_shortlist.csv`** (20 empresas, sectores TI y
  Arquitectura/Ingeniería) fue la primera pasada, sin emails — se dejó
  como registro del proceso.
- **`validacion/lote_02_verificado.csv` es el lote real, listo para
  enviar**: 12 empresas con email genérico **verificado de verdad**
  (encontrado en su propia web o en un directorio empresarial fiable, no
  inventado ni adivinado por patrón), repartidas en **4 sectores**: TI
  (Madrid), Arquitectura/Ingeniería (Canarias + C. Valenciana), Servicios
  empresariales/consultoría (Madrid) y Medioambiente/residuos (Castilla y
  León) — estos dos últimos añadidos el 28/09 con el mismo criterio
  cuantitativo de la Fase 1, no por intuición.
- De ~22 empresas revisadas una a una: 12 confirmadas, y el resto
  descartadas explícitamente — no "email no encontrado, se envía igual a
  lo que haya". Excluidas por ser en realidad grandes empresas pese al
  contrato pequeño (Accenture, Indra, Deloitte, NTT Data, MathWorks, Auren
  Auditores — red de 60+ oficinas en 11 países, Ecija Legal — 4º despacho
  de España), por estar disuelta (Vivaticket Ibérica, extinguida en 2025),
  o por no tener email público localizable (dejadas fuera de este lote,
  no en la plantilla con hueco vacío).
