#!/bin/bash
# Refresca los datos de licitaciones (PLACSP + Bilbao + TendersGuru) y
# republica el Artifact publicado. Pensado para correr por cron dos veces
# al día en esta máquina (tiene acceso normal a internet, sin las
# restricciones de red del entorno en la nube).
set -uo pipefail

# cron corre con un PATH mínimo que no incluye ~/.local/bin (donde vive el
# binario `claude`) ni /opt/homebrew/bin; lo añadimos explícitamente.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$(dirname "$0")/.."
LOG="data/refresh.log"
mkdir -p data

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >>"$LOG"

.venv/bin/python -m backend.export --pages 15 >>"$LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "export.py falló, no se publica nada." >>"$LOG"
  exit 1
fi

TOTAL=$(.venv/bin/python -c "import json; print(json.load(open('data/licitaciones.json'))['total'])" 2>>"$LOG")
if [ -z "$TOTAL" ] || [ "$TOTAL" -eq 0 ]; then
  echo "Export vacío (total=$TOTAL), no se publica nada." >>"$LOG"
  exit 1
fi

cp data/licitaciones.json artifact/licitaciones.json

PROJECT_DIR="$(pwd)"
ARTIFACT_URL="https://claude.ai/code/artifact/d9469c85-6ceb-49d4-8cf4-d98b04b2f9a2"

PUBLISH_OUTPUT=$(claude -p "Llama a la herramienta Artifact con action='publish', url='${ARTIFACT_URL}' (esta es la URL canónica exacta, úsala tal cual, NO la sustituyas ni preguntes nada), file_path='${PROJECT_DIR}/artifact/index.html', files={\"licitaciones.json\": \"${PROJECT_DIR}/artifact/licitaciones.json\"}. No pases favicon. No hagas ninguna otra llamada ni preguntes nada: llama a la herramienta directamente con esos parámetros. Responde solo con 'PUBLICADO' seguido del número de versión si la llamada tuvo éxito, o 'ERROR: <motivo>' si falló." \
  --allowedTools "Artifact" 2>>"$LOG")
echo "$PUBLISH_OUTPUT" >>"$LOG"

if echo "$PUBLISH_OUTPUT" | grep -q "PUBLICADO"; then
  echo "OK: publicado (total=$TOTAL)." >>"$LOG"
else
  echo "FALLO: la publicación no se confirmó (total=$TOTAL, datos locales sí actualizados)." >>"$LOG"
  exit 1
fi
