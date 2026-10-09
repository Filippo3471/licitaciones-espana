# Runbook: dominio + Google Workspace + Instantly.ai para el outreach de Adjuplica

Preparado el 09-10-2026 (ronda 4 del founder-lab). Todo lo de aquí está listo en código/copy; lo que necesita tarjeta, verificación de teléfono o clic humano lo marco con **🔴 TÚ**. Nada se envía realmente hasta el último paso, y ese paso necesita tu confirmación explícita y específica (cuántos, a quién, cuándo) — no basta con "adelante" general, es la norma del proyecto desde el principio.

## 0. Por qué un dominio nuevo (no adjuplica.es/.com)

El outreach en frío a volumen (hasta 100/día) quema reputación de envío mientras se calienta. Si se hace desde el dominio principal y algo se marca como spam, puede arrastrar también el email transaccional (confirmaciones, alertas) del producto real. Un dominio aparte protege eso — es desechable si algo va mal, el principal no.

**Candidatos comprobados disponibles hoy (whois, 09-10-2026):**
1. **contactoadjuplica.com** (recomendado — se lee en español, claramente ligado a la marca)
2. tryadjuplica.com
3. adjuplicacontratos.com

🔴 **TÚ**: compra uno (Namecheap, Porkbun o similar, ~10-15€/año) y dime cuál elegiste.

## 1. Google Workspace sobre el dominio nuevo

1. 🔴 **TÚ**: ve a workspace.google.com → Business Starter (~6-7€/usuario/mes) → usa el dominio que compraste en el paso 0.
2. Crea **2-3 buzones** (no uno solo — repartir el volumen entre varios buzones reduce el riesgo de que uno se marque como spam y tira toda la campaña). Sugerencia: `filippo@`, `ventas@`, `contacto@` + el dominio nuevo.
3. Workspace te pedirá verificar que el dominio es tuyo (un registro TXT) y te dará los valores de MX, SPF y DKIM. Apúntalos — van en el paso 2.

🔴 **TÚ**: necesitas tarjeta y, probablemente, verificación por teléfono. No puedo hacer esto por ti.

## 2. Registros DNS (en el panel del registrador del dominio nuevo)

Añade estos 4 registros (los valores exactos de MX/DKIM te los da Workspace en el paso 1 — aquí van los que sí puedo darte ya, sin esperar a Workspace):

| Tipo | Nombre | Valor | Para qué |
| --- | --- | --- | --- |
| TXT | @ | `v=spf1 include:_spf.google.com ~all` | Autoriza a Google a enviar en nombre del dominio |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:TU_EMAIL_REAL@aqui.com` | DMARC en modo "solo observar" las primeras 2-3 semanas — nunca `p=reject` desde el día 1 |
| MX | @ | (los 5 valores que te da Workspace, `ASPMX.L.GOOGLE.COM` etc.) | Para poder recibir en los buzones nuevos |
| TXT | `google._domainkey` (o el que indique Workspace) | (la clave DKIM que genera Workspace) | Firma criptográfica anti-spoofing — sin esto, Gmail/Outlook marcan el correo como sospechoso |

🔴 **TÚ**: pega estos registros en el DNS de tu registrador y espera 24-48h a que propaguen antes de seguir.

## 3. Instantly.ai

1. 🔴 **TÚ**: crea cuenta en instantly.ai (plan Growth es el más barato con warmup incluido, ~37$/mes al cambio).
2. Conecta los 2-3 buzones de Workspace del paso 1 (Instantly pide usuario/contraseña de app o conexión OAuth con Google — sigue su asistente).
3. **Activa el "warmup" de Instantly y déjalo corriendo 2-3 semanas antes de mandar nada real.** Esto no es opcional: un dominio nuevo que manda 100 emails/día desde el día 1 se marca como spam casi seguro, y entonces se pierde el dominio entero, no solo esa tanda.
4. Mientras calienta, yo dejo listos:
   - La campaña en 2 pasos (ver abajo) — cópiala tal cual en el editor de secuencias de Instantly.
   - El CSV de la lista: corre `.venv/bin/python validacion/generar_mini_informes_outreach.py` y luego `.venv/bin/python validacion/exportar_csv_instantly.py` → sube `validacion/instantly_import.csv` en Leads → Import leads.
   - Límite diario en la propia campaña de Instantly: empieza en 20/día (no 100) el primer lote real, igual que `validacion/enviar_outreach.py` ya hace para el canal de Resend — subir a 100/día solo si la tasa de respuesta/rebote del primer lote sale bien.

## 4. La secuencia (2 pasos, tono Hormozi + Ogilvy — ver founder/offer.md)

**Paso 1** (día 0) — usa las variables `{{empresa}}`, `{{mini_informe}}`, `{{link_informe}}` del CSV:

> Asunto: `{{empresa}}: quién está ganando en tu sector ahora mismo`
>
> Hola,
>
> {{mini_informe}}
>
> Lo hemos sacado de un informe gratuito de tu sector, sin registro: {{link_informe}}
>
> Una propuesta concreta: mandadnos un pliego que ya ganasteis o perdisteis — uno cuyo resultado ya conocéis. Lo analizamos gratis y comparáis vosotros mismos si el GO/NO-GO (requisito por requisito de solvencia, con la cita exacta del pliego) coincide con lo que de verdad pasó. Sin compromiso, sin tarjeta.
>
> Si cuadra, el primer pliego real que analicéis después cuesta 5 € (a partir del segundo, 19 €, o la suscripción si licitáis a menudo). Y si alguna vez el GO/NO-GO os dice que cumplís un requisito y la mesa de contratación os excluye por ese mismo requisito, os devolvemos el análisis y os regalamos 3 meses de Básico. El riesgo es nuestro, no vuestro.
>
> ¿Nos mandáis un pliego ya cerrado para probarlo?
>
> Un saludo,
> Filippo (Adjuplica)

**Paso 2** (día 4, solo a quien no respondió — Instantly lo hace automático por "no reply"):

> Asunto: `Re: {{empresa}}: quién está ganando en tu sector ahora mismo`
>
> Hola de nuevo,
>
> Sé que esto compite con el correo que de verdad importa, así que voy directo: si alguna vez perdéis un concurso por un requisito de solvencia que se os pasó, o por llegar tarde con un documento, eso es exactamente lo que comprobamos gratis con un pliego vuestro ya cerrado — sin coste, sin compromiso.
>
> Si no es el momento, respondiendo "BAJA" no os vuelvo a escribir.
>
> Filippo

Ambos emails incluyen la baja explícita (obligatoria por LSSI/RGPD en comunicaciones comerciales en España) — Instantly también añade su propio link de "unsubscribe" automático, déjalo activo además del texto.

## 5. Antes de pulsar "enviar" en Instantly

Esto es lo único que de verdad requiere tu autorización explícita, por lote:
- Confirma el **número exacto** de contactos de esta primera tanda (recomendado: 20, no 100 — es un dominio nuevo recién calentado).
- Confirma que los 2-3 buzones llevan **al menos 2-3 semanas** de warmup antes de este envío.
- Dime cuándo quieres que lance ese lote concreto — lo hago yo mismo navegando Instantly si me das acceso, o lo lanzas tú y me avisas para seguir el seguimiento.

## Lo que ya está listo en el repo (código, no cuentas)
- `validacion/generar_mini_informes_outreach.py` — genera los mini-informes personalizados.
- `validacion/exportar_csv_instantly.py` — los convierte en CSV de importación para Instantly.
- `founder/offer.md` / `founder/summary.md` — por qué el email está escrito así (ecuación de valor, panel 70%→80%).
- La garantía ya está también en la web (`docs/index.html`, modal de precios) — si alguien que recibe el email visita la web antes de responder, ve la misma promesa.
