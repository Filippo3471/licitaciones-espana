# Licitaciones públicas España

Buscador de licitaciones públicas **abiertas** en España, con un histórico
de **adjudicaciones** (quién gana, por cuánto, compitiendo con cuántos).

**Sitio en vivo (se actualiza solo, dos veces al día):**
https://filippo3471.github.io/licitaciones-espana/

Para cada licitación abierta:

- **Qué pliegos y documentos hay que presentar** (PCAP, PPT y anexos), con
  enlace directo de descarga del PDF oficial.
- **Requisitos de solvencia y declaraciones exigidas** (a qué tipo de
  empresa le aplica: capacidad de obrar, solvencia técnica/económica, etc.).
- **Zona geográfica** de ejecución (comunidad autónoma / provincia, vía
  códigos NUTS oficiales).
- **Estado, tipo de contrato, sector (CPV) y plazo de presentación.**

Para cada adjudicación en el histórico: empresa ganadora (nombre, NIF,
ciudad), importe adjudicado vs. importe licitado, fecha, y cuántas empresas
compitieron.

## Fuentes de datos

| Fuente | Tipo | Cobertura |
|---|---|---|
| [PLACSP](https://contrataciondelestado.es) | Oficial (feed ATOM/CODICE) | Administración General del Estado, CCAA y entidades locales agregadas |
| [Generalitat de Catalunya](https://analisi.transparenciacatalunya.cat) | Oficial (Socrata) | Cataluña (en buena parte no solapa con PLACSP) |
| [TED](https://ted.europa.eu) | Oficial (Search API v3, UE) | Contratos por encima de umbrales europeos, toda España |
| Ayuntamiento de Bilbao | Oficial (JSON propio) | Bilbao |
| [TendersGuru](https://tenders.guru) | Terceros | Intermitente — el conector es defensivo y no rompe el pipeline si está caído |

No hay scraping de HTML ni bypass de ningún sistema de acceso: todo son
feeds/APIs oficiales de datos abiertos.

## Arquitectura

```
backend/
  fetch.py, parser.py     # PLACSP: descarga + parseo CODICE (con CA bundle FNMT)
  sources/                # Un conector por fuente adicional (catalunya, ted, bilbao, tenders_guru)
  db.py                   # SQLite — acumula histórico, nunca se purga
  export.py               # Combina todas las fuentes en licitaciones.json + adjudicaciones.json
scripts/
  refresh_and_publish.sh  # Orquesta export + publica en docs/ vía git push
docs/                     # Lo que sirve GitHub Pages (index.html + los dos JSON)
artifact/                 # Copia para publicar a mano en un Claude Artifact (opcional, no automático)
```

Dos veces al día (cron, 09:00 y 15:00 hora de España) `scripts/refresh_and_publish.sh`:
1. Vuelve a descargar todas las fuentes y las guarda en `data/licitaciones.db` (SQLite, acumulativo — el histórico de adjudicaciones crece con cada ejecución).
2. Exporta el estado actual a `data/licitaciones.json` (solo licitaciones abiertas) y `data/adjudicaciones.json` (histórico, tope 4000 más recientes).
3. Copia ambos a `docs/` y hace `git commit` + `git push` — GitHub Pages recoge el cambio solo.

### Por qué GitHub Pages y no solo un Claude Artifact

La primera versión publicaba directamente en un Claude Artifact desde cron,
llamando a `claude -p`. Dos límites reales de esa vía, confirmados
probando en el propio entorno de cron:

- `claude -p` (modo headless) **no expone la herramienta Artifact en
  absoluto** — no es un permiso denegado, es que ese modo no la tiene.
- `claude --bg` (agente en segundo plano) sí la tiene, pero exige aceptar
  una comprobación de "workspace trust" que solo se puede pasar de forma
  interactiva; saltarla con `--dangerously-skip-permissions` está
  bloqueado por el clasificador de seguridad, con razón.

`git push` no depende de ninguna herramienta de Claude, así que es la vía
robusta para publicar sin supervisión. El Claude Artifact original sigue
existiendo para republicar a mano si se quiere, pero ya no es la copia
"viva".

## Instalación

```bash
cd ~/licitaciones-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gh auth login   # una vez, para que git push funcione sin pedir contraseña
```

## Actualizar manualmente

```bash
python -m backend.export --pages 15
```

## Automatización (ya instalada)

```
0 9,15 * * * ~/licitaciones-app/scripts/refresh_and_publish.sh >> ~/licitaciones-app/data/cron.log 2>&1
```

Logs en `data/refresh.log`. El cron **solo corre si el Mac está despierto**
a esa hora — no hay cola de alcance si estaba dormido.

## Nota técnica sobre el certificado TLS de PLACSP

`contrataciondelestado.es` usa un certificado emitido por la CA oficial
española **"AC RAIZ FNMT-RCM SERVIDORES SEGUROS"**. Ese root no está en el
almacén de confianza por defecto de macOS/curl en muchos sistemas fuera de
España, así que `backend/fetch.py` combina el bundle estándar de `certifi`
con la cadena FNMT incluida en `backend/certs/` — nunca se desactiva la
verificación TLS.

## Limitaciones conocidas

- **Sin deduplicación entre fuentes**: una misma licitación por encima de
  umbrales UE puede aparecer tanto en PLACSP como en TED. No hay matching
  implementado todavía (~23% de solape de órganos observado).
- Euskadi tiene API propia pero su documentación estaba rota/inaccesible al
  investigarla; Navarra tiene portal de datos abiertos pero no respondió en
  las pruebas. Ninguna de las dos está integrada.
- `app.py` (Flask) y `templates/` son la versión local original, previa al
  sitio estático — ya no es la vía principal, se mantiene sin garantías.
- Los requisitos de solvencia estructurados dependen de lo que cada órgano
  haya rellenado en CODICE; cuando faltan, siempre están completos en el
  PCAP descargable.
