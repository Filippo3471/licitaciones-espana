"""Bloque 10.3 del prompt "copiloto de ofertas": script de envío del
primer contacto (el mini-informe del Bloque 10.2), con salvaguardas.

AVISO operativo (ronda 4 del founder-lab, 09-10-2026): el email que
construye este script le pide al destinatario que mande un pliego ya
cerrado para analizarlo gratis. Ese flujo HOY es manual — no hay un
botón de autoservicio en la web para subir un pliego ya decidido y
compararlo con el resultado real. Si se manda un lote real y alguien
responde con un pliego, hace falta procesarlo a mano (vía la cuenta de
empresa del fundador) hasta que se construya ese flujo.

SIEMPRE en modo DRY_RUN salvo que se pase --live explícitamente, Y ADEMÁS
se escriba CONFIRMO_ENVIO=SI en el entorno. Ninguna de las dos cosas por
separado basta — esto es intencional: nunca se manda un lote real de
emails sin una autorización explícita y específica para ese lote,
siguiendo la norma del proyecto. Aun en modo --live, si no hay
RESEND_API_KEY / ALERTS_FROM_EMAIL configurados, el script no envía nada
(nunca simula un envío como si hubiera salido).

Salvaguardas (todas activas también en DRY_RUN, para que el propio
dry-run ya muestre a quién tocaría excluir):
  - Excluye siempre estado = 'baja' (la lista de exclusión es la propia
    columna estado de outreach_contacts, no un fichero aparte).
  - Nunca contacta dos veces a la misma empresa en menos de 14 días
    (se mira fecha_contacto).
  - Solo contactos con canal = 'email' y con email real (los de
    'telefono'/'linkedin' se listan pero se omiten: ese contacto es
    manual).
  - Límite diario configurable con --limite (empieza en 20).
  - Requiere que haya un mini-informe generado para ese contact_id en
    validacion/outreach_mini_informes.json (Bloque 10.2) — si no lo hay,
    se omite en vez de mandar un email genérico.

Uso (revisión, no manda nada):
    .venv/bin/python validacion/enviar_outreach.py
    .venv/bin/python validacion/enviar_outreach.py --limite 10

Uso (envío real — requiere las dos condiciones a la vez):
    export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... RESEND_API_KEY=... ALERTS_FROM_EMAIL=...
    export CONFIRMO_ENVIO=SI
    .venv/bin/python validacion/enviar_outreach.py --live --limite 20
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
INFORMES_PATH = RAIZ / "validacion" / "outreach_mini_informes.json"
NO_REPETIR_DIAS = 14


def cargar_informes() -> dict[str, dict]:
    if not INFORMES_PATH.exists():
        print(f"No existe {INFORMES_PATH}. Genera primero los mini-informes "
              f"con validacion/generar_mini_informes_outreach.py.", file=sys.stderr)
        sys.exit(1)
    datos = json.loads(INFORMES_PATH.read_text(encoding="utf-8"))
    return {str(d["contact_id"]): d for d in datos}


def cargar_candidatos(session: requests.Session, base_url: str) -> list[dict]:
    r = session.get(
        f"{base_url}/rest/v1/outreach_contacts",
        params={"estado": "neq.baja", "select": "id,empresa,nif,canal,email,estado,fecha_contacto"},
    )
    r.raise_for_status()
    return r.json()


def elegible(contacto: dict) -> tuple[bool, str]:
    if contacto["estado"] == "baja":
        return False, "dado de baja"
    if contacto["canal"] != "email" or not contacto.get("email"):
        return False, f"canal {contacto['canal']} (no es email, requiere contacto manual)"
    fecha = contacto.get("fecha_contacto")
    if fecha:
        try:
            dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        except ValueError:
            dt = None
        if dt and (datetime.now(timezone.utc) - dt) < timedelta(days=NO_REPETIR_DIAS):
            return False, f"contactado hace menos de {NO_REPETIR_DIAS} días ({fecha})"
    return True, ""


def construir_email(informe: dict) -> tuple[str, str]:
    # Ronda 4 del founder-lab (09-10-2026, founder/offer.md): lo que mueve
    # la aguja no es el precio ni la promesa, es la probabilidad percibida
    # de que el análisis acierte (ecuación de valor de Hormozi). El email
    # lleva la prueba verificable (pliego ya conocido) y la garantía por
    # delante, en vez de pedir que se fíen a ciegas. Tono: Ogilvy (dato
    # concreto del propio sector del lector, una sola promesa, una sola
    # llamada a la acción, cero adjetivos sin respaldo) + Hormozi (riesgo
    # invertido: la empresa no arriesga nada, Adjuplica sí).
    asunto = f"{informe['empresa']}: quién está ganando en {informe['sector']} ahora mismo"
    cuerpo = (
        f"Hola,\n\n"
        f"{informe['mini_informe']}\n\n"
        f"Lo hemos sacado de un informe gratuito de tu sector, sin registro: {informe['link_con_utm']}\n\n"
        f"Una propuesta concreta: mandadnos un pliego que ya ganasteis o perdisteis — uno cuyo resultado "
        f"ya conocéis. Lo analizamos gratis y comparáis vosotros mismos si el GO/NO-GO (requisito por "
        f"requisito de solvencia, con la cita exacta del pliego) coincide con lo que de verdad pasó. "
        f"Sin compromiso, sin tarjeta.\n\n"
        f"Si cuadra, el primer pliego real que analicéis después cuesta 5 € (a partir del segundo, 19 €, "
        f"o la suscripción si licitáis a menudo). Y si alguna vez el GO/NO-GO os dice que cumplís un "
        f"requisito y la mesa de contratación os excluye por ese mismo requisito, os devolvemos el "
        f"análisis y os regalamos 3 meses de Básico. El riesgo es nuestro, no vuestro.\n\n"
        f"¿Nos mandáis un pliego ya cerrado para probarlo?\n\n"
        f"Si no os interesa, respondiendo \"BAJA\" no os volvemos a escribir.\n\n"
        f"Un saludo,\nFilippo (Adjuplica)"
    )
    return asunto, cuerpo


def enviar_resend(api_key: str, de: str, para: str, asunto: str, cuerpo: str) -> None:
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"from": de, "to": [para], "subject": asunto, "text": cuerpo},
    )
    r.raise_for_status()


def marcar_contactado(session: requests.Session, base_url: str, contact_id: str) -> None:
    r = session.patch(
        f"{base_url}/rest/v1/outreach_contacts",
        params={"id": f"eq.{contact_id}"},
        json={"estado": "contactado", "fecha_contacto": datetime.now(timezone.utc).isoformat()},
    )
    r.raise_for_status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=20, help="Máximo de envíos en esta ejecución (por defecto 20).")
    parser.add_argument("--live", action="store_true", help="Intenta enviar de verdad. Requiere además CONFIRMO_ENVIO=SI en el entorno.")
    args = parser.parse_args()

    modo_live = args.live and os.environ.get("CONFIRMO_ENVIO") == "SI"
    if args.live and not modo_live:
        print("--live pedido pero falta CONFIRMO_ENVIO=SI en el entorno: se queda en DRY_RUN por seguridad.", file=sys.stderr)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Faltan SUPABASE_URL y/o SUPABASE_SERVICE_ROLE_KEY en el entorno.", file=sys.stderr)
        sys.exit(1)

    informes = cargar_informes()
    session = requests.Session()
    session.headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"})
    base_url = url.rstrip("/")

    candidatos = cargar_candidatos(session, base_url)
    print(f"{len(candidatos)} contactos (sin dar de baja) en outreach_contacts. Modo: {'ENVÍO REAL' if modo_live else 'DRY_RUN'}. Límite: {args.limite}.")

    resend_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("ALERTS_FROM_EMAIL")
    if modo_live and not (resend_key and from_email):
        print("ENVÍO REAL pedido pero faltan RESEND_API_KEY / ALERTS_FROM_EMAIL: no se envía nada (se trata como DRY_RUN).", file=sys.stderr)
        modo_live = False

    enviados, omitidos, sin_informe = 0, 0, 0
    for c in candidatos:
        if enviados >= args.limite:
            print(f"Límite diario de {args.limite} alcanzado. Quedan {len(candidatos) - candidatos.index(c)} contactos para otra ejecución.")
            break
        ok, motivo = elegible(c)
        if not ok:
            omitidos += 1
            continue
        informe = informes.get(str(c["id"]))
        if not informe:
            sin_informe += 1
            continue

        asunto, cuerpo = construir_email(informe)
        if not modo_live:
            print(f"DRY-RUN -> {c['empresa']} <{c['email']}> | asunto: {asunto}")
        else:
            enviar_resend(resend_key, from_email, c["email"], asunto, cuerpo)
            marcar_contactado(session, base_url, c["id"])
            print(f"ENVIADO -> {c['empresa']} <{c['email']}>")
        enviados += 1

    print(f"\nResumen: {enviados} {'enviados' if modo_live else 'simulados (DRY_RUN)'}, "
          f"{omitidos} omitidos (baja / no-email / contactado hace <{NO_REPETIR_DIAS} días), "
          f"{sin_informe} sin mini-informe generado todavía.")


if __name__ == "__main__":
    main()
