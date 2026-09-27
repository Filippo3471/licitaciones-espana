# Validación — Fase 1: investigación de escritorio

Generado: 2026-09-27. Fuente de los números propios: `validacion/desk_research.py`
sobre `data/licitaciones.db` (solo lectura), snapshot del 27/09/2026 —
ver `validacion/desk_research.json` para el detalle completo por sector y
por sector×CCAA. Metodología y limitaciones de esos números al final de
este documento.

## 1. Sectores objetivo recomendados

**71 — Servicios de arquitectura, ingeniería y construcción** y
**72 — Servicios de tecnologías de la información (TI)**.

| | Abiertas hoy | Importe total abiertas | Importe medio | Adjudicadas/mes (aprox.) | % adjudicadas con ≤3 licitadores |
|---|---|---|---|---|---|
| 71 Arquitectura/Ingeniería | 211 | 229,2 M€ | 1,09 M€ | ~37,6 | 68,5% |
| 72 TI | 85 | 167,1 M€ | 2,01 M€ | ~25,8 | 71,6% |

Por qué estos dos y no el sector nº1 por importe (**45 — Construcción y obra
civil**, 1.560 M€ en 842 licitaciones abiertas): a pesar de tener el mayor
volumen agregado, el importe medio (~1,85M€) y el tipo de obra (grandes
civiles) apuntan a que lo dominan contratistas grandes con departamentos de
licitación propios — mal encaje para un SaaS temprano dirigido a pymes que
hoy buscan a mano. 71 y 72 combinan importe medio alto (deals que
justifican pagar por una herramienta), alta cuota de "pocos licitadores"
(hueco para pymes que hoy no se enteran a tiempo) y, sobre todo en TI, un
comprador que ya está acostumbrado a pagar por software — la hipótesis de
disposición a pagar es más barata de probar ahí que en un sector que nunca
ha comprado una suscripción SaaS.

Candidato de reserva si 71/72 no validan: **79 — Servicios empresariales
(consultoría, limpieza, seguridad, publicidad)** — mayor frecuencia mensual
(~45,6 adjudicaciones/mes) y alto volumen (197 abiertas), pero importe
medio bajo (418k€) y categoría muy heterogénea; menos limpio como ICP
inicial. Ver también la opción de pivote a "consultoras de licitaciones"
(intermediarios que preparan ofertas para terceros) si el dolor en 71/72
resulta bajo — ya prevista en los criterios de decisión de la Fase 5.

## 2. Competencia — agregadores españoles de licitaciones

Todo lo que sigue viene de fuentes públicas citadas; no he podido acceder a
paneles de reseñas exhaustivos (Trustpilot/Google solo tenían cobertura
real para uno de los competidores) — lo marco explícitamente donde no hay
dato.

- **Quiero Licitar** ([precios](https://quierolicitar.com/precios)) —
  freemium: Free (2 análisis IA/mes, histórico 30 días), Pro 19€/mes,
  MAX 49€/mes, Enterprise 89€/mes (todos con descuento ~10% en anual).
  Indexa +9.000 licitaciones abiertas de Estado, 19 CCAA y administración
  local en tiempo real, según su propia web.
- **LicitaFacil** ([web](https://licitafacil.pro/)) — plan único, 50€/mes
  (60,50€ IVA incl.), sin límites por categoría, prueba gratuita 14 días,
  1 usuario por suscripción.
- **Gobierto Contratación** ([planes](https://contratos.gobierto.es/planes)) —
  5 niveles desde 300€/año (Inicio, 3 alertas) hasta 1.490€/mes
  (Enterprise, alertas ilimitadas, API); apunta más a mediana/gran empresa
  o consultoras que a autónomos/pymes pequeñas por el rango de precio.
- **Licitaciones.io** ([Trustpilot](https://es.trustpilot.com/review/licitaciones.io)) —
  4,6/5 sobre 24 reseñas. Única queja concreta encontrada en las reseñas
  visibles: *"echo de menos la posibilidad de exportar reportes
  detallados"* (la empresa respondió que lo añadiría). Sin más quejas
  sustantivas visibles. No publica precios en la web pública.
- **rTenders / iaLicitaciones** ([precios](https://rtenders.com/)) — **no
  es un competidor español**: precios en libras, terminología UK ("ITT"),
  cumplimiento UK (DPA/DPIA/SSO). Lo incluyo solo como referencia de
  producto adyacente: es el más parecido en forma a lo que haríamos en
  Fase 3 del MVP original (ayuda-pliego con IA) — Starter £35/mes, Pro
  £99/mes, Business £349/mes (10 usuarios), Enterprise a medida.
- **Diario de Licitaciones** — descartado como comparable: precios
  publicados en una moneda distinta al euro y órdenes de magnitud muy
  altos, lo que sugiere que es una plataforma para otro mercado
  (probablemente Latinoamérica), no España.

**Lectura honesta:** no encontré foros ni reseñas negativas sustanciales
sobre ningún competidor español más allá del comentario de exportación de
Licitaciones.io. Esto NO significa que no existan quejas — significa que
no las encontré con búsqueda pública en el tiempo disponible. No lo
declaro como "sin quejas" en las hipótesis de abajo; lo trato como dato
insuficiente.

Nuestro precio propuesto en `plans.json` (Básico 49€, Pro 149€, Equipo
399€) queda por encima de Quiero Licitar y LicitaFacil (19-50€) y por
debajo de los niveles altos de Gobierto (300-1.490€). Vale la pena tenerlo
en cuenta cuando se analicen los precios mencionados en las entrevistas
(hipótesis H4 más abajo) — puede que 149€/mes para el plan Pro esté caro
frente a la referencia de mercado visible.

## 3. Cinco hipótesis críticas

Cada una con su métrica (comportamiento observable, no opinión) y el
umbral de éxito/fracaso que usaré en `validacion/analisis.md` (Fase 5).
H5 usa literalmente el criterio de decisión ya fijado por el fundador.

| # | Hipótesis | Métrica | Éxito | Fracaso |
|---|---|---|---|---|
| H1 | Buscan licitaciones a mano hoy y les cuesta tiempo real | % que dedica ≥2h/semana a buscar manualmente en portales | ≥60% | <30% |
| H2 | Se les escapan licitaciones relevantes por no enterarse a tiempo | % que reporta ≥1 licitación perdida en el último año por no verla a tiempo | ≥50% | <20% |
| H3 | Ya existe disposición a pagar por esto (no hay que crear la necesidad) | % que ya paga o ha pagado por una herramienta/servicio de licitaciones | ≥30% | <10% |
| H4 | Nuestro rango de precio (49-149€/mes) es compatible con lo que el mercado ya paga | Precio medio mencionado espontáneamente por quienes pagan/pagarían | ≥30€/mes | mayoría dice <15€/mes o "gratis" |
| H5 | El interés se traduce en preventa real pagada, no solo declarada | Nº de preventas "fundador" pagadas por sector | ≥3 pagadas en un sector (criterio ya fijado para "construir") | 0 pagos con ≥15 entrevistas completas en el sector |

Ninguna de estas se da por validada ni refutada todavía — no hay
entrevistas reales aún (Fase 2 en adelante). Este documento es solo la
base cuantitativa y de mercado sobre la que se diseñará el guion de
entrevista.

## 4. Metodología y limitaciones de los datos propios

- `estado='PUB'` es un snapshot del momento de ejecución del script — no
  hay serie histórica de "licitaciones abiertas" porque el crawl de este
  proyecto solo lleva activo ~1 semana.
- La frecuencia mensual de adjudicaciones se calcula sobre
  `fecha_adjudicacion` de los últimos 12 meses, tal y como aparece en el
  feed de PLACSP. El feed no es un archivo histórico completo — está
  sesgado hacia los meses recientes (en los datos: 5.440 adjudicaciones en
  septiembre-2026 frente a 35 en enero-2026). La cifra de "adjudicadas/mes"
  es orientativa, no una serie temporal fiable mes a mes.
- "Pocos licitadores" = ≤3 ofertas recibidas. Es un umbral propio, no un
  estándar del sector — lo elegí porque separa razonablemente adjudicaciones
  con competencia real de adjudicaciones casi en solitario, pero es
  discutible y está documentado aquí para que cualquiera pueda cuestionarlo.
- Solo se leyó `data/licitaciones.db`, en modo `mode=ro` (solo lectura,
  aplicado a nivel de conexión SQLite, no solo por convención).
