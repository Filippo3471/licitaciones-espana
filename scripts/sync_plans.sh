#!/bin/bash
# plans.json es la única fuente de verdad (ver su campo "_nota"). Este
# script solo copia — nunca edites las copias directamente, edita
# plans.json en la raíz y vuelve a correr esto.
set -euo pipefail
cd "$(dirname "$0")/.."
cp plans.json docs/plans.json
cp plans.json artifact/plans.json
cp plans.json supabase/functions/_shared/plans.json
echo "plans.json sincronizado a docs/, artifact/ y supabase/functions/_shared/"
