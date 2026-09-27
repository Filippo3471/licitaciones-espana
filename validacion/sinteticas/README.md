# Entrevistas SINTÉTICAS — piloto del guion (Fase 2)

**Todo lo que hay en esta carpeta es SINTÉTICO** (personas generadas por
LLM, ver `personas.json`). Esto NO es validación real y está **excluido**
de cualquier análisis en `validacion/analisis.md`. Sirve solo para probar
el guion antes de hablar con ninguna empresa real.

## Qué se probó

10 personas sintéticas distintas contra el guion real
(`supabase/functions/_shared/entrevista.ts`), vía la función de testing
`validacion-simular-entrevista` (protegida por secreto compartido, no
enlazada desde ningún frontend público): un escéptico de "otra herramienta
más", dos usuarios de competidores reales (Quiero Licitar, LicitaFacil),
una empresa de bajo dolor (no persigue licitaciones activamente), una
persona muy evasiva/vaga, un decisor único con alto dolor y alta
disposición a pagar, una constructora grande fuera de los sectores
objetivo (para ver el comportamiento fuera de foco), una empresa que ya
paga a una gestoría externa, una persona con prisa que corta la
conversación, y alguien que pregunta el precio dos veces muy pronto.

## Resultado

Las 10 terminaron correctamente (marcador `[FIN_ENTREVISTA]` disparado por
el propio guion, entre 4 y 19 turnos, todas por debajo del límite de 25).
Reglas críticas verificadas en las transcripciones:

- Una pregunta cada vez: cumplido en las 10.
- Repreguntar ante respuestas vagas: cumplido (ver `05_arquitectura_bilbao_evasivo.json`, 19 turnos por lo evasivo de las respuestas, sin bucles infinitos).
- No vender ni hablar de precio durante la exploración: cumplido incluso bajo presión directa y repetida (ver `10_ti_malaga_usa_competidor_pregunta_precio.json`, pregunta el precio dos veces antes del cierre y el guion aplaza ambas veces a "el equipo te escribe con la horquilla").
- Informe con datos reales (no inventados): confirmado — el informe mostrado en cada entrevista usó la API pública real de licitaciones.json, con licitaciones y órganos reales (Aena, Ayuntamientos, Generalitat, etc.), filtradas por el sector/CCAA que la propia conversación fue estableciendo.

## Ajuste hecho al guion tras el piloto

En `09_arquitectura_madrid_con_prisa.json` la persona corta la
conversación a media exploración ("tengo que dejarlo, me esperan"). El
guion respondió bien (no insistió, cerró con el informe + reacción +
preventa en un único mensaje) pero eso técnicamente rompe la regla "una
pregunta cada vez". Era el comportamiento correcto, no un fallo, así que
en vez de "arreglarlo" para que lo cumpliera a rajatabla (lo que habría
significado seguir preguntando a alguien que ya dijo que se iba), se
documentó como excepción explícita en el propio guion:

> "EXCEPCIÓN EXPLÍCITA a 'una pregunta cada vez': si la persona dice que
> tiene que irse ya... es correcto condensar en un único mensaje final el
> informe + la reacción + la preventa + la despedida."

No se encontró ningún otro fallo del guion en este piloto. Esto no
significa que el guion sea perfecto — 10 personas sintéticas no sustituyen
entrevistas reales, que pueden traer comportamientos que un LLM
role-playing no reproduce (silencios largos, cambios de tema bruscos,
malentendidos genuinos del lenguaje). Se revisará de nuevo tras las
primeras entrevistas reales.

## Hallazgo de producto (no es un fallo del guion, es una señal para Fase 5)

En `10_ti_malaga_usa_competidor_pregunta_precio.json`, la persona (que ya
paga 50€/mes por LicitaFacil) valoró el informe de listado con un 2/5,
explicando que es "prácticamente lo mismo" que ya recibe por alerta, y que
el valor real estaría en el análisis automático del pliego (detectar
requisitos de solvencia y cláusulas escondidas), no en el listado en sí.
Al ser una entrevista sintética, esto NO se usa como dato de análisis —
pero si aparece un patrón parecido en entrevistas reales, apunta a que
"resumen de pliego / elegibilidad" pesa más que el simple listado en la
priorización de funcionalidades de la Fase 5.
