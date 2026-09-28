#!/bin/bash
# Refresca los datos de licitaciones (PLACSP + Catalunya + TED + Bilbao +
# TendersGuru) y publica el sitio en GitHub Pages (docs/) vía git push.
# Pensado para correr por cron dos veces al día en esta máquina.
#
# Nota histórica: esto publicaba antes en un Claude Artifact llamando a
# `claude -p`, pero ese modo no expone la herramienta Artifact (confirmado
# probándolo), y el modo que sí la tiene (--bg) exige una comprobación de
# confianza de workspace que no se puede aceptar sin sesión interactiva.
# git push no depende de ninguna herramienta de Claude, así que funciona
# desatendido sin ese problema.
set -uo pipefail

# cron corre con un PATH mínimo que no incluye ~/.local/bin ni
# /opt/homebrew/bin (donde viven `gh`/`git` de Homebrew); lo añadimos.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# cron tampoco define USER/LOGNAME; algunas herramientas (gh incluido)
# los necesitan para resolver credenciales guardadas en el Keychain.
export USER="${USER:-$(id -un)}"
export LOGNAME="${LOGNAME:-$USER}"

# git config user.name/email no está fijado a nivel global ni local en este
# repo; en vez de tocar la config de git, se lo pasamos por variables de
# entorno solo para los commits de este script.
export GIT_AUTHOR_NAME="Filippo Di Nola"
export GIT_AUTHOR_EMAIL="filippodinola@Filippos-MacBook-Pro.local"
export GIT_COMMITTER_NAME="Filippo Di Nola"
export GIT_COMMITTER_EMAIL="filippodinola@Filippos-MacBook-Pro.local"

# El credential helper osxkeychain (usado por el remote HTTPS de origin) no
# es accesible desde un proceso cron sin sesión interactiva — el push
# fallaba con "could not read Username... Device not configured". En vez de
# tocar el remote guardado en .git/config, se hace push por SSH a una URL
# explícita usando una deploy key dedicada de solo este repo (sin passphrase,
# permisos 600), sin depender del Keychain.
DEPLOY_KEY="$HOME/.ssh/licitaciones_deploy_key"
export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
PUSH_URL="git@github.com:Filippo3471/licitaciones-espana.git"

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

# Copia opcional para el Claude Artifact (publicación manual, ya no
# automática — se queda igual por si se quiere republicar a mano alguna vez).
cp data/licitaciones.json artifact/licitaciones.json
[ -f data/adjudicaciones.json ] && cp data/adjudicaciones.json artifact/adjudicaciones.json

# Copia real que sirve GitHub Pages.
cp data/licitaciones.json docs/licitaciones.json
[ -f data/adjudicaciones.json ] && cp data/adjudicaciones.json docs/adjudicaciones.json

# Regenera la página de estadísticas (HTML estático, sin fetch por JS, para
# que los rastreadores de IA que no ejecutan JavaScript puedan leerla) con
# los datos recién exportados. Una página de estadísticas con cifras
# desactualizadas es peor que no tenerla, así que se recalcula en cada ciclo.
.venv/bin/python -m backend.estadisticas >>"$LOG" 2>&1

if git diff --quiet -- docs/ && git diff --cached --quiet -- docs/; then
  echo "OK: sin cambios en los datos, no hace falta publicar (total=$TOTAL)." >>"$LOG"
  exit 0
fi

git add docs/ >>"$LOG" 2>&1
git commit -q -m "Actualización automática de datos ($(date -u +%Y-%m-%dT%H:%M:%SZ))" >>"$LOG" 2>&1
if git push "$PUSH_URL" HEAD:master >>"$LOG" 2>&1; then
  echo "OK: publicado en GitHub Pages (total=$TOTAL)." >>"$LOG"
else
  echo "FALLO: git push falló (total=$TOTAL, commit local sí se creó)." >>"$LOG"
  exit 1
fi
