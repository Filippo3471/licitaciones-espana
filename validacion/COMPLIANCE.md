# Compliance — Fase 4 (reclutamiento)

**Estado: asumido por el fundador, no hay departamento legal.** El 28/09/2026
el fundador confirmó explícitamente ("no existe compliance... tienes todos
los permisos y todas mis autorizaciones") que no hay una función legal
interna que revise esto, y que asume él mismo los riesgos documentados
abajo. Esto no los elimina — solo cambia quién los acepta. Si en el futuro
hay asesoría legal externa, debería revisar este documento antes de escalar
el volumen de envíos más allá de lotes pequeños de prueba.

Esto sigue sin ser una autorización para enviar un lote concreto — cada
lote (destinatarios, sector, plantilla) se confirma aparte antes de
enviarse, por regla explícita del propio fundador en el Prompt 4.

## LSSI-CE (comunicaciones comerciales por email)

- El mensaje de invitación es una comunicación comercial no solicitada a
  un email corporativo genérico (no a una persona identificada). La LSSI
  exige: identificación clara del remitente, indicación explícita de que
  es publicidad/comunicación comercial, y la posibilidad de oponerse
  (baja) de forma sencilla y gratuita.
- **Riesgo**: enviar desde una cuenta de Gmail personal (decisión ya
  tomada para esta fase) puede dañar la entregabilidad (spam) y no
  transmite la misma confianza/identificación de remitente que un dominio
  corporativo con SPF/DKIM configurado. No es un incumplimiento de la
  LSSI en sí, pero legal debería confirmar si es aceptable para el
  volumen y la reincidencia (recordatorios) previstos.
- **Riesgo**: el límite de envío de una cuenta Gmail normal (no
  Workspace) es bajo (documentado como referencia externa: Google indica
  límites diarios de envío en cuentas gratuitas, hay que confirmar cifra
  exacta vigente antes de enviar el primer lote real). Con lotes de
  máximo 50 no debería ser problema, pero hay que vigilarlo si hay varios
  lotes el mismo día.
- **Mitigación implementada**: la web incluye ya un enlace de baja
  funcional (ver más abajo) y la plantilla de invitación (pendiente de
  redactar) incluirá identificación del remitente, etiqueta de
  comunicación comercial, origen del contacto y enlace de baja en un
  clic, tal y como pide el propio Prompt 4.

## RGPD

- **Base legal**: interés legítimo (prospección B2B a un email
  corporativo genérico, no a una persona física identificada, sobre una
  empresa que ya participa públicamente en licitaciones — dato de origen
  público). Legal debe confirmar si esto es defendible como interés
  legítimo o si hace falta otra base.
- **Minimización**: la invitación va a un email corporativo genérico
  (`info@`, `contacto@`, etc.), nunca a una persona con nombre. Si durante
  la entrevista la persona da su nombre o email personal, no se guarda en
  la tabla de análisis (`validacion_entrevistas`), solo sector/provincia/
  tamaño — ver `supabase/migrations/20260927030000_validacion_entrevistas.sql`.
- **Derecho de supresión**: implementado de forma funcional (no solo
  prometido en el texto) — la propia página de entrevista tiene un enlace
  "Borrar mis datos" que borra la fila de `validacion_entrevistas` al
  momento, sin depender de que nadie procese la solicitud a mano.
- **Riesgo pendiente**: no hay todavía un mecanismo de baja para la
  invitación en sí (antes de llegar a la entrevista) — alguien que reciba
  el email pero nunca abra el enlace de entrevista no tiene forma de
  ejercer su derecho de oposición salvo responder al email. Hay que
  decidir si se construye un enlace de baja dedicado antes del primer
  envío real (recomendado) o si basta con "responder a este email".
- **Conservación**: no hay todavía una política de cuánto tiempo se
  conservan las transcripciones tras acabar el estudio de validación —
  legal debería fijar un plazo (p.ej. borrar todo lo no convertido en
  cliente a los N meses de cerrar el estudio).

## AI Act (art. 50 — obligación de transparencia)

- Implementado: la página de entrevista identifica al entrevistador como
  IA antes de cualquier pregunta, y no se genera ninguna pregunta sin
  consentimiento explícito (checkbox), aplicado por código (la función
  rechaza generar la primera pregunta sin `consentimiento_en` registrado).
- **Riesgo**: el email de invitación en sí (antes de llegar a la
  conversación) no menciona todavía que la conversación posterior será
  con una IA — solo se dice dentro de la propia entrevista. Legal debería
  confirmar si basta con decirlo al entrar a la conversación o si debe
  anticiparse ya en el asunto/cuerpo del email de invitación.

## Riesgos operativos (no legales, pero relevantes)

- Enviar desde un Gmail personal mezcla la identidad personal del
  fundador con una comunicación comercial — si alguien responde con
  quejas o el email se marca como spam repetidamente, puede afectar la
  cuenta personal, no solo la campaña.
- No hay todavía un proceso de gestión de rebotes (bounces) — si un email
  genérico no existe, el lote no tiene forma automática de detectarlo.

## Estado

**Asumido por el fundador (28/09/2026), no hay legal interno.** Riesgos
conocidos y aceptados: entregabilidad/límites de Gmail personal, ausencia
de baja dedicada en el propio email (mitigado parcialmente con
`docs/baja.html`, pero solo alcanzable si el destinatario llega a abrir el
enlace de entrevista), base de interés legítimo sin confirmación legal
externa, y ausencia de gestión automática de rebotes. Cada lote sigue
necesitando confirmación explícita y separada antes de enviarse.
