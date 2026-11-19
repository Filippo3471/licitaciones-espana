# MENTOR_LOG — mentor-negocio-autonomo

## Diagnóstico (19-11-2026)

**Qué vende, a quién, a qué precio**: Adjuplica/licitaciones-app vende a PYMEs
españolas que licitan a contratos públicos un análisis de "¿cumplo la
solvencia de este pliego?" con cita real de página/cláusula, generado por IA.
Oferta de entrada: 1 mes gratis, después 29 €/mes (ver
`~/harvey/data/plantilla_respuesta_si.md`). Resultado soñado del cliente:
saber en 24h, sin leer 100 páginas de pliego, si les merece la pena presentar
oferta — y no ser excluidos por un requisito de solvencia que no vieron.

**Etapa**: primeros clientes / validación (founder/offer.md habla de "ronda
4"; hay suscripciones Stripe, pero bajo volumen).

**Números**: no hay panel de analítica consultado en esta sesión — pendiente
de estimar en una próxima vuelta (revenue real, CAC, churn).

**Competencia**: no auditada en esta sesión (fuera de alcance — se centró en
diagnosticar la propia oferta primero, por orden Hormozi: oferta antes de
tráfico).

## El cuello de botella (2-3 frases)

La captación en frío (Adjuplica.3/Consultoras, Instantly) ya tiene volumen de
leads reales (261, verificados, listos). El cuello de botella NO es
generación de leads: es que la oferta más fuerte del producto — el análisis
GO/NO-GO con cita real de cláusula — existe en producción
(`supabase/functions/ayuda-pliego/index.ts`, desplegada, con `ANTHROPIC_API_KEY`
configurada desde el 25-09-2026) pero **no se usa en el email de captación
fría**. Los emails salientes (Email 1B) solo *ofrecen* comprobarlo, nunca lo
*muestran*, porque un análisis previo mío (equivocado) concluyó que esa
función no existía. Eso deja la oferta más fuerte sin usar donde más importa:
el primer contacto frío, que es exactamente donde un dato concreto y
verificable (no genérico) decide si abren el email o no.

## Plan corto (orden de impacto)

1. **Generar el análisis GO/NO-GO real para las ~20 licitaciones con más
   leads matched**, usando la función ya desplegada (`ayuda-pliego`) — no
   reconstruirla a mano. Esto da material real y citado para el Email 1A.
   — *Bloqueado en ejecución automática*: la función exige una sesión de
   usuario real autenticada (JWT), no la service_role key (lo confirmé
   leyendo el código: usa `userClient.auth.getUser()`), y cada llamada nueva
   consume cuota de uso + coste real de API bajo la cuenta del usuario. Por
   el protocolo de este mentor, una llamada a una API de pago con coste
   real requiere tu confirmación explícita — ver pregunta al usuario.
2. Con ese análisis real, construir Adjuplica.3-A1/A2 (Email 1A "con
   análisis") y comparar su tasa de apertura/respuesta contra B1/B2 — ya
   construidas y en pausa, 261 leads.
3. Rellenar `adjuplica/responder_si.py` (quien responda "sí" a un email)
   usando el mismo resumen cacheado en `pliego_summaries`, en vez del
   placeholder que dejé en `plantilla_respuesta_si.md`.
4. Medir: tasa de respuesta A1/A2 vs B1/B2 en los primeros 7 días tras
   lanzar — es la prueba YC de si la cita real mueve la aguja o no, antes
   de invertir en escalar el parser a las 1000+ licitaciones restantes.
5. Una vez validado, automatizar la llamada a `ayuda-pliego` dentro de
   `ciclo_diario.sh` para que cada lead nuevo con match ≥7 puntos llegue
   con su análisis ya generado (hoy: ninguno lo tiene).

## Qué hice en esta sesión (resumen)

- Localicé y leí `supabase/functions/ayuda-pliego/index.ts` completo:
  confirmé que SÍ existe el motor GO/NO-GO con cita real, cacheado en
  `pliego_summaries`, y entendí exactamente su contrato (auth, gating de
  uso, formato de respuesta).
- Corregí mi propio error anterior (había dicho que esa función no existía
  tras mirar solo el backend Python).
- Generé una prueba de concepto real leyendo a mano 1 PCAP (Metro de Madrid,
  Shopify, 164 páginas) con el mismo criterio "nunca inventar" → guardada en
  `~/harvey/data/analisis_top20.json`. Confirmé que escalar esto a mano a
  20 pliegos es demasiado caro — la vía correcta es la función ya
  desplegada, no releer PDFs en el chat.
- No modifiqué ningún archivo de `licitaciones-app` (solo lectura) — no hizo
  falta rama nueva todavía.

## Pendiente de tu aprobación

**Dinero / coste de API real**: ¿apruebas que ejecute, vía navegador con tu
sesión real ya logueada en la web, la función "Ayuda con el pliego" para las
~17-20 licitaciones top (una por una, igual que lo harías tú a mano), para
generar el análisis real y cachearlo en `pliego_summaries`? Coste estimado:
céntimos por licitación (ya tienes la API key de Anthropic configurada); el
límite real es la cuota de tu plan, no el dinero. Si prefieres, lo haces tú
mismo clicando en la web — 20 clics — y yo luego leo el resultado cacheado
para construir los emails A1/A2.

## Corrección del diagnóstico (19-11-2026, 22:42)

El usuario confirmó, viendo el Instantly real: el producto está bien (GO/NO-GO
funciona, landing ya con CTA+FAQ, pipeline de datos real). El cuello de
botella es FOCO y ejecución de venta, no el producto — prueba: 6 campañas
(Adjuplica.1/.2/.3/.3-B1/.3-B2/Consultoras), la mayoría pausadas a medias
(Adjuplica.2: 420 enviados de una lista mucho mayor, pausada al 1%;
Adjuplica.1: pausada al 15%), y la cuenta de prueba del propio fundador en
plan Free. Decisión: dejar de construir variantes nuevas. Lanzar B1/B2 (el
lote más limpio y reciente) y no tocar nada más hasta tener señal real
(respuestas) durante 7-14 días. Congelado hasta entonces: nuevas campañas,
nuevos lotes, nuevas variantes de email, el parser GO/NO-GO manual.

## Otras decisiones pendientes (ya reportadas antes en este chat)

- Lanzar Adjuplica.3-B1/B2 (261 leads, en pausa).
- Outlook test del Email 1B/1A — nunca se completó (no había cuenta de
  prueba disponible).
