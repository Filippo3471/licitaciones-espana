# Embudo 100% async — sin llamadas, en ningún punto

Motivo: Filippo tiene day job, cero disponibilidad para llamadas en directo.
Rediseño completo, no un parche — cada paso debe poder pasar sin que
Filippo esté presente en tiempo real.

## El embudo nuevo

```
Email (gancho real: su contrato ganado o el importe de su zona)
  → CTA directo al producto: https://filippo3471.github.io/licitaciones-espana/
  → sube su pliego real → GO/NO-GO en 2 minutos, gratis de ver
  → paga 5€ el primer análisis completo, o empieza la prueba de 14 días (sin tarjeta)
  → Stripe cobra y gestiona todo — cero intervención humana
  → si contesta pidiendo "verlo explicado": se le manda el vídeo (no una llamada)
```

La entrevista de IA (`entrevista.html`) deja de ser el CTA principal. Se
queda como canal secundario opcional para quien prefiera no tocar el
producto todavía — pero ya no es el camino por defecto, precisamente
porque medimos que nadie lo termina (0 de 22).

## Nuevo CTA de email (variante D — para el próximo lote, después del checkpoint)

**Asunto:** igual que las otras variantes (con el dato real)

**Cuerpo:**

Hola,

Soy Filippo, fundador de Adjuplica. Vi que {{Empresa Nombre}} ha sido
adjudicataria de contratos públicos recientes.

He montado la herramienta para que la pruebes tú mismo, sin hablar con
nadie: sube tu próximo pliego y en 2 minutos sabes si cumples cada
requisito de solvencia, con la cita exacta de la página para que lo
compruebes.

👉 Probarlo ahora: https://filippo3471.github.io/licitaciones-espana/

El primer análisis son 5€. Si prefieres probarlo sin compromiso, hay 14
días gratis, sin tarjeta.

Esto es una comunicación comercial. Os escribimos porque {{Empresa
Nombre}} aparece como adjudicataria en datos públicos de contratación
(PLACSP) — no tenemos ni usamos ningún otro dato vuestro.

Si no queréis recibir más mensajes como este, daos de baja en un clic:
{{unsubscribe_link}}

Un saludo,
Filippo — Adjuplica

## Si alguien contesta pidiendo "verlo explicado" / una demo

Plantilla de respuesta async (nunca ofrecer una llamada):

> Claro — te dejo un vídeo corto (3 min) donde lo pruebo con un pliego
> real, así lo ves sin que tengamos que cuadrar agendas: [enlace al vídeo]
>
> Si después de verlo te queda alguna duda concreta, contéstame aquí
> mismo por email y te respondo en cuanto pueda (normalmente en 24-48h).

## Guion del vídeo (2-3 min, se graba UNA vez, sirve para siempre)

1. (0:00-0:20) "Soy Filippo, fundador de Adjuplica. Esto es lo que hace
   en 2 minutos, con un pliego real que ya ganó alguien."
2. (0:20-1:00) Pantalla: subir el pliego (PDF o enlace), mostrar el
   análisis cargando.
3. (1:00-2:00) Mostrar el GO/NO-GO por requisito, clicar una cita para
   enseñar que lleva a la página exacta del PDF oficial — el punto clave
   de diferenciación (nadie más lo hace, confirmado en la investigación
   de competencia).
4. (2:00-2:40) Checklist de documentación/plazos, histórico de
   adjudicaciones del sector.
5. (2:40-3:00) Cierre: "5€ el primer análisis, o 14 días gratis sin
   tarjeta. El enlace está abajo." — sin pedir nada más, sin CTA a
   hablar contigo.

Grabarlo con QuickTime (Mac, gratis, Cmd+Shift+5) o Loom. Se sube una vez
a YouTube/Loom como "no listado" y el enlace se reutiliza para siempre.

## Soporte post-venta

Email únicamente, con expectativa explícita de 24-48h — nunca se ofrece
una llamada ni se sugiere "podemos hablar". Si en el futuro el volumen de
dudas async se vuelve demasiado para gestionar entre el day job, la
siguiente palanca es una FAQ en el propio producto, no llamadas.

## Excepción puntual (05-11-2026)

El informe "Top 20 Reasons Startups Fail" (The Revenue Coaches) marca
"founder avoids selling to customers" en el 44% de startups que no
llegan a sus primeros 50 clientes. La regla de cero llamadas sigue en
pie como política general (viene de una limitación real: day job, cero
tiempo) — pero no es evitación por evitación. Excepción explícita: si un
prospecto real y cualificado del plan Equipo/Consultora (399€/mes, el
ticket más alto) pide explícitamente hablar, no cerrar la puerta del
todo — 15 minutos puntuales no rompen la política general, perder un
cliente de 399€/mes por rigidez sí sería un error. No se ofrece la
llamada de forma proactiva en ningún mensaje; solo se acepta si el
propio prospecto la pide.
