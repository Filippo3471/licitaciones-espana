# Licitaciones públicas España

Sitio web local que agrega las licitaciones publicadas en la **Plataforma de
Contratación del Sector Público (PLACSP)** — la fuente oficial del Ministerio
de Hacienda que centraliza (mediante mecanismos de agregación) las
licitaciones de la Administración General del Estado, comunidades autónomas
y administración local — y muestra para cada una:

- **Qué pliegos y documentos hay que presentar** (PCAP, PPT y anexos), con
  enlace directo de descarga del PDF oficial.
- **Requisitos de solvencia y declaraciones exigidas** (a qué tipo de
  empresa le aplica: capacidad de obrar, solvencia técnica/económica, etc.).
- **Zona geográfica** de ejecución (comunidad autónoma / provincia, vía
  códigos NUTS oficiales).
- **Estado, tipo de contrato (obras/servicios/suministros), sector (CPV) y
  plazo de presentación.**

## Cómo funciona

1. `backend/update.py` descarga el feed ATOM/CODICE público de
   `contrataciondelestado.es` (formato oficial de datos abiertos del
   Ministerio de Hacienda) y lo guarda en una base SQLite local
   (`data/licitaciones.db`).
2. `app.py` (Flask) sirve un sitio web local para explorar y filtrar esos
   datos.

No hay scraping de HTML ni bypass de ningún sistema de acceso: se usa
exclusivamente el feed de sindicación oficial que la propia plataforma
publica para reutilización de datos.

## Instalación

```bash
cd ~/licitaciones-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Descargar / actualizar datos

```bash
python -m backend.update --pages 15
```

Cada página trae hasta ~500 entradas. El feed es un histórico continuo de
altas y cambios, así que con 10-15 páginas ya se cubren varios miles de
expedientes recientes, incluyendo las licitaciones actualmente abiertas
(estado `PUB`). Vuelve a ejecutar este comando cuando quieras refrescar los
datos (puedes ponerlo en un cron, ver más abajo).

## Arrancar el sitio

```bash
python app.py
```

Abre `http://127.0.0.1:5050`. Por defecto solo muestra licitaciones con
estado **"Abierta"** (`PUB`); desde los filtros puedes cambiar el estado,
la comunidad autónoma, el tipo de contrato, el sector (CPV) o buscar texto
libre.

## Actualización automática (opcional)

Para refrescar los datos cada mañana, añade a tu crontab (`crontab -e`):

```
0 8 * * * cd ~/licitaciones-app && .venv/bin/python -m backend.update --pages 15 >> data/update.log 2>&1
```

## Nota técnica sobre el certificado TLS

`contrataciondelestado.es` usa un certificado emitido por la CA oficial
española **"AC RAIZ FNMT-RCM SERVIDORES SEGUROS"** (FNMT — Fábrica Nacional
de Moneda y Timbre). Ese root no está en el almacén de confianza por
defecto de macOS/curl en muchos sistemas fuera de España, así que
`backend/fetch.py` combina el bundle estándar de `certifi` con la cadena de
certificados FNMT incluida en `backend/certs/` para verificar la conexión
correctamente — en ningún momento se desactiva la verificación TLS
(`verify=False`).

## Limitaciones conocidas (prototipo local)

- Cubre las licitaciones agregadas en la PLACSP. Algunas comunidades
  autónomas con plataforma propia (Aragón, Euskadi, Illes Balears...) solo
  aparecen aquí si están federadas/agregadas a la PLACSP; si no, habría que
  añadir un conector específico a su portal.
- Los requisitos de solvencia estructurados dependen de lo que cada órgano
  de contratación haya rellenado en el formulario CODICE; cuando no vienen
  detallados, siempre están completos dentro del PCAP (pliego
  administrativo) descargable.
- El feed usado es el "histórico continuo" (`licitacionesPerfilesContratanteCompleto3`);
  para una cobertura exhaustiva de años completos existen también los ZIPs
  anuales de datos abiertos en
  `https://contrataciondelestado.es/wps/portal/plataforma/datos_abiertos`.

## Estructura del proyecto

```
app.py                  # Sitio web Flask
backend/
  fetch.py               # Descarga del feed ATOM/CODICE (con CA bundle FNMT)
  parser.py               # Parseo del XML CODICE a dicts
  db.py                    # Esquema SQLite y upsert
  update.py                 # CLI: orquesta descarga + parseo + guardado
  cpv.py                     # Tabla de sectores CPV (2 dígitos)
  nuts_es.py                  # Tabla de comunidades autónomas (NUTS-2)
  codelists.py                 # Traducción de códigos de estado/contrato
  certs/                        # Cadena de certificados FNMT
templates/               # Plantillas Jinja2 (listado + detalle)
data/                     # Base de datos SQLite (se genera al actualizar)
```
