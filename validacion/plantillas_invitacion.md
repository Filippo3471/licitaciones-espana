# Plantillas de invitación — Lote 01 (TI Madrid + Arquitectura/Ingeniería Canarias/C.Valenciana)

Estado: **DRY_RUN — no enviado.** Pendiente de tu aprobación explícita
(nº de destinatarios, sector, plantilla) antes de mandar nada, y de que
confirmes que legal ha revisado `validacion/COMPLIANCE.md`.

Variables: `{{empresa_nombre}}`, `{{n_abiertas_zona}}`,
`{{importe_total_zona}}`, `{{ccaa}}`, `{{sector}}`, `{{token}}`. El dato
concreto (nº de licitaciones e importe) sale de
`validacion/desk_research.json`, no está inventado — las mismas columnas
ya existen en los CSV de cada lote, así que Instantly las rellena solas al
importar el CSV como leads (no hace falta tocar nada más).

`{{link_entrevista}}` se sustituye por la URL real de la entrevista por IA
que ya existe en producción (`docs/entrevista.html` + la Edge Function
`entrevista-validacion`, que busca la empresa en `validacion_empresas`
por el `token` — un solo parámetro, no hace falta pasar empresa/sector/etc.
en la URL, el servidor ya los tiene):
```
https://filippo3471.github.io/licitaciones-espana/entrevista.html?t={{token}}
```
**Importante**: ese `token` del CSV es el mismo que usa `validacion_empresas`
— para las empresas de lote_02/03/04 YA EXISTE una fila ahí (creada el
28-09-2026, cuando se mandó el primer envío real). No generes tokens
nuevos para esas 30 filas ni las trates como leads nuevos — ver nota más
abajo sobre qué lotes son reutilizables.

`{{link_baja}}` se sustituye por la variable nativa de baja de Instantly
— en su editor, busca el merge tag de "Unsubscribe link" en el selector
de variables (suele ser `{{unsubscribe_link}}`) y úsalo en su lugar; no
hace falta construir nada propio, todas las plataformas de cold email lo
traen de serie y es obligatorio que esté presente.

---

## Variante A — dato por delante

**Asunto:** {{empresa_nombre}}: {{n_abiertas_zona}} licitaciones abiertas en {{ccaa}} ahora mismo

Hola,

Soy Filippo, fundador de Adjuplica. Os escribo porque vimos que
{{empresa_nombre}} ha sido adjudicataria de contratos públicos recientes
(dato público de PLACSP) — así que puede que esto os interese.

Ahora mismo hay **{{n_abiertas_zona}} licitaciones abiertas** en vuestro
sector en {{ccaa}}, por un importe total de **{{importe_total_zona}}€**.

Estamos investigando cómo buscan hoy licitaciones empresas como la
vuestra, antes de construir nada más. A cambio de 5 minutos en una
conversación por chat (con un asistente de IA, no una llamada), os
mandamos gratis el informe completo y personalizado de licitaciones
abiertas para vuestro sector y zona.

👉 [Empezar (5 min)](https://filippo3471.github.io/licitaciones-espana/entrevista.html?t={{token}})

Esto es una comunicación comercial. Os escribimos porque
{{empresa_nombre}} aparece como adjudicataria en datos públicos de
contratación (PLACSP) filtrados por vuestro sector de actividad — no
tenemos ni usamos ningún otro dato vuestro.

Si no queréis recibir más mensajes como este, [daos de baja en un
clic]({{unsubscribe_link}}), sin nada que justificar.

Un saludo,
Filippo — Adjuplica

---

## Variante B — pregunta por delante

**Asunto:** ¿Cuánto tiempo perdéis buscando licitaciones cada semana?

Hola,

Soy Filippo, fundador de Adjuplica. Estamos hablando con
empresas de vuestro sector en {{ccaa}} para entender cómo buscáis hoy
licitaciones públicas — antes de construir nada, queremos saber si de
verdad hace falta.

Como agradecimiento por 5 minutos de conversación por chat (con un
asistente de IA, no una llamada — os lo explicamos al entrar), os
mandamos gratis un informe con las **{{n_abiertas_zona}} licitaciones
abiertas ahora mismo** en vuestro sector en {{ccaa}} ({{importe_total_zona}}€ en total).

👉 [Empezar (5 min)](https://filippo3471.github.io/licitaciones-espana/entrevista.html?t={{token}})

Esto es una comunicación comercial. Os escribimos porque
{{empresa_nombre}} aparece como adjudicataria en datos públicos de
contratación (PLACSP) filtrados por vuestro sector de actividad — no
tenemos ni usamos ningún otro dato vuestro.

Si no queréis recibir más mensajes como este, [daos de baja en un
clic]({{unsubscribe_link}}), sin nada que justificar.

Un saludo,
Filippo — Adjuplica

---

## Seguimiento 1 — día 3 (paso 2 de la secuencia en Instantly)

**Asunto:** ¿viste nuestro email?

Hola de nuevo,

Por si se perdió entre el resto de correos: {{n_abiertas_zona}}
licitaciones abiertas ahora mismo en vuestro sector en {{ccaa}}
({{importe_total_zona}}€ en total), y os mandamos gratis el informe
completo a cambio de 5 minutos en un chat con IA.

👉 [Empezar (5 min)](https://filippo3471.github.io/licitaciones-espana/entrevista.html?t={{token}})

Si no os interesa, [daos de baja en un clic]({{unsubscribe_link}}).

Un saludo,
Filippo — Adjuplica

---

## Seguimiento 2 — día 7 (paso 3 de la secuencia en Instantly)

**Asunto:** último correo

Último correo, no insisto más. Si alguna vez os habéis preguntado cuántas
licitaciones reales hay abiertas en vuestro sector ahora mismo, lo tenéis
aquí gratis, sin compromiso:

👉 [Verlo (5 min)](https://filippo3471.github.io/licitaciones-espana/entrevista.html?t={{token}})

Si no, perdonad la insistencia y [daos de baja aquí]({{unsubscribe_link}}).

Un saludo,
Filippo — Adjuplica

---

## 🔴 Estado real de los 3 lotes (verificado contra la base de datos, no de memoria)

- **lote_01 (20 empresas)**: 0 tienen email real — no son leads enviables.
- **lote_02/03/04 (30 empresas)**: YA tienen fila en `validacion_empresas`,
  creada el 28-09-2026 — es decir, **ya recibieron el email real** (y
  algunas un seguimiento el 02-10). De esas 30: **24 en estado "enviada"**
  (ya contactadas, no son un primer touch) y **6 en estado "baja"** — estas
  6 están dadas de baja de verdad y **no se les puede volver a escribir,
  por ninguna vía, nunca**.
- **Conclusión**: no hay leads nuevos listos para un primer envío ahora
  mismo en estos 3 lotes. Hace falta sourcing nuevo (DataForSEO/Google
  Maps) antes de poder cargar una campaña real en Instantly.

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
