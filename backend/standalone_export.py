#!/usr/bin/env python3
"""Script autocontenido (sin dependencias del paquete backend/) que descarga
las licitaciones públicas abiertas de España desde varias fuentes y escribe
un JSON unificado. Pensado para ejecutarse en un entorno efímero (p.ej. un
agente en la nube) sin acceso al resto del repositorio.

Fuentes:
  - PLACSP (contrataciondelestado.es) — feed oficial ATOM/CODICE
  - Ayuntamiento de Bilbao / Open Data Euskadi — JSON oficial
  - TendersGuru (tenders.guru) — agregador de terceros, best-effort

Uso:
  python3 standalone_export.py --pages 15 --out licitaciones.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import requests
except ImportError:
    print("Falta 'requests'. Instala con: pip install requests certifi", file=sys.stderr)
    raise

# --------------------------------------------------------------------------
# Certificados: contrataciondelestado.es usa la CA oficial española FNMT
# ("AC RAIZ FNMT-RCM SERVIDORES SEGUROS"), que no siempre está en el
# almacén de confianza por defecto. La combinamos con el bundle de certifi
# en vez de desactivar la verificación TLS.
# --------------------------------------------------------------------------
FNMT_ROOT = """-----BEGIN CERTIFICATE-----
MIICbjCCAfOgAwIBAgIQYvYybOXE42hcG2LdnC6dlTAKBggqhkjOPQQDAzB4MQsw
CQYDVQQGEwJFUzERMA8GA1UECgwIRk5NVC1SQ00xDjAMBgNVBAsMBUNlcmVzMRgw
FgYDVQRhDA9WQVRFUy1RMjgyNjAwNEoxLDAqBgNVBAMMI0FDIFJBSVogRk5NVC1S
Q00gU0VSVklET1JFUyBTRUdVUk9TMB4XDTE4MTIyMDA5MzczM1oXDTQzMTIyMDA5
MzczM1oweDELMAkGA1UEBhMCRVMxETAPBgNVBAoMCEZOTVQtUkNNMQ4wDAYDVQQL
DAVDZXJlczEYMBYGA1UEYQwPVkFURVMtUTI4MjYwMDRKMSwwKgYDVQQDDCNBQyBS
QUlaIEZOTVQtUkNNIFNFUlZJRE9SRVMgU0VHVVJPUzB2MBAGByqGSM49AgEGBSuB
BAAiA2IABPa6V1PIyqvfNkpSIeSX0oNnnvBlUdBeh8dHsVnyV0ebAAKTRBdp20LH
sbI6GA60XYyzZl2hNPk2LEnb80b8s0RpRBNm/dfF/a82Tc4DTQdxz69qBdKiQ1oK
Um8BA06Oi6NCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMCAQYwHQYD
VR0OBBYEFAG5L++/EYZg8k/QQW6rcx/n0m5JMAoGCCqGSM49BAMDA2kAMGYCMQCu
SuMrQMN0EfKVrRYj3k4MGuZdpSRea0R7/DjiT8ucRRcRTBQnJlU5dUoDzBOQn5IC
MQD6SmxgiHPz7riYYqnOK8LZiqZwMR2vsJRM60/G49HzYqc8/5MuB1xJAWdpEgJy
v+c=
-----END CERTIFICATE-----
"""

FNMT_INTERMEDIATE = """-----BEGIN CERTIFICATE-----
MIIDhjCCAwugAwIBAgIQE45rvt8g9ZRcG2z2KbQvSjAKBggqhkjOPQQDAzB4MQsw
CQYDVQQGEwJFUzERMA8GA1UECgwIRk5NVC1SQ00xDjAMBgNVBAsMBUNlcmVzMRgw
FgYDVQRhDA9WQVRFUy1RMjgyNjAwNEoxLDAqBgNVBAMMI0FDIFJBSVogRk5NVC1S
Q00gU0VSVklET1JFUyBTRUdVUk9TMB4XDTE4MTIyMDEwMjAzOFoXDTMzMTIyMDEw
MjAzOFowcDELMAkGA1UEBhMCRVMxETAPBgNVBAoMCEZOTVQtUkNNMQ4wDAYDVQQL
DAVDZXJlczEYMBYGA1UEYQwPVkFURVMtUTI4MjYwMDRKMSQwIgYDVQQDDBtBQyBT
RVJWSURPUkVTIFNFR1VST1MgVElQTzIwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAASP
ktCp3OKHGKWghcWSgWzaV4PqEEDK7lwaZzlofqY3gU8CTEq5frt6rBYYiJzojh7Z
mZ/1vcca5wrd/ydOw9Ofp7LoOLYQwGSBrP5EVqi5eat3L34zEWRL+S81/t9Uqsij
ggFgMIIBXDASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB/wQEAwIBBjAdBgNV
HQ4EFgQUxfIFTvQ3cuTqTwJXA/2GlgWuUI8wEQYDVR0gBAowCDAGBgRVHSAAMIGa
BggrBgEFBQcBAQSBjTCBijBBBggrBgEFBQcwAYY1aHR0cDovL29jc3Bmbm10c3Ny
LmNlcnQuZm5tdC5lcy9vY3Nwc3NyL09jc3BSZXNwb25kZXIwRQYIKwYBBQUHMAKG
OWh0dHA6Ly93d3cuY2VydC5mbm10LmVzL2NlcnRzL0FDUkFJWlNFUlZJRE9SRVNT
RUdVUk9TLmNydDBGBgNVHR8EPzA9MDugOaA3hjVodHRwOi8vd3d3LmNlcnQuZm5t
dC5lcy9jcmxzL0FSTFNFUlZJRE9SRVNTRUdVUk9TLmNybDAfBgNVHSMEGDAWgBQB
uS/vvxGGYPJP0EFuq3Mf59JuSTAKBggqhkjOPQQDAwNpADBmAjEAnJshOoWfFFqu
eqe+3yzdUXqZaeinywJfJagUJAVRHfK3+82W3E5JHJIVbQ5tEnvzAjEAxygUimAw
yn6g78HFOc/0Se4/KxDcZe6iysFEptrXQWbek73XgAQu2VlMDmESuDJD
-----END CERTIFICATE-----
"""

FEED_URL = (
    "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3.atom"
)
HEADERS = {"User-Agent": "licitaciones-app/0.1 (uso personal, prototipo)"}


def _ca_bundle(tmp_dir: Path) -> str:
    import certifi

    bundle = tmp_dir / "ca-bundle.pem"
    base = Path(certifi.where()).read_text()
    bundle.write_text(base + "\n" + FNMT_INTERMEDIATE + "\n" + FNMT_ROOT)
    return str(bundle)


# --------------------------------------------------------------------------
# Tablas de códigos (CODICE / CPV / NUTS)
# --------------------------------------------------------------------------
TIPO_CONTRATO = {"1": "Suministros", "2": "Servicios", "3": "Obras", "21": "Gestión de servicios públicos", "31": "Concesión de servicios", "32": "Concesión de obras"}

CPV_DIVISIONES = {
    "03": "Agricultura, ganadería, pesca, silvicultura", "09": "Productos petrolíferos, combustibles, electricidad y energía",
    "14": "Minería y minerales", "15": "Alimentación, bebidas, tabaco", "16": "Maquinaria agrícola",
    "18": "Prendas de vestir, calzado", "19": "Cuero y textil", "22": "Impresión y artes gráficas",
    "24": "Productos químicos", "30": "Máquinas de oficina, informática", "31": "Maquinaria y aparatos eléctricos",
    "32": "Equipos de radio, TV, comunicaciones", "33": "Equipos médicos, farmacia, cosmética",
    "34": "Vehículos, transporte", "35": "Equipos de seguridad, defensa", "37": "Instrumentos musicales, deportivos, juegos",
    "38": "Equipos de laboratorio, óptica, precisión", "39": "Mobiliario, artículos del hogar, limpieza",
    "41": "Agua", "42": "Maquinaria industrial", "43": "Maquinaria de minería, construcción",
    "44": "Materiales de construcción", "45": "Construcción y obra civil", "48": "Paquetes de software y sistemas de información",
    "50": "Servicios de reparación y mantenimiento", "51": "Servicios de instalación", "55": "Servicios de hostelería y restauración",
    "60": "Servicios de transporte", "63": "Servicios de apoyo al transporte, agencias de viaje", "64": "Servicios postales y de telecomunicaciones",
    "65": "Servicios públicos (agua, energía)", "66": "Servicios financieros y de seguros", "70": "Servicios inmobiliarios",
    "71": "Servicios de arquitectura, ingeniería y construcción", "72": "Servicios de tecnologías de la información (TI)",
    "73": "Servicios de investigación y desarrollo (I+D)", "75": "Servicios de administración pública y defensa",
    "76": "Servicios relacionados con el sector del petróleo y gas", "77": "Servicios agrícolas, forestales, jardinería",
    "79": "Servicios empresariales: publicidad, limpieza, consultoría, seguridad", "80": "Servicios de educación y formación",
    "85": "Servicios de salud y acción social", "90": "Servicios medioambientales, saneamiento, residuos",
    "92": "Servicios recreativos, culturales y deportivos", "98": "Otros servicios comunitarios, sociales y personales",
}

CCAA_POR_NUTS2 = {
    "ES11": "Galicia", "ES12": "Principado de Asturias", "ES13": "Cantabria", "ES21": "País Vasco",
    "ES22": "Comunidad Foral de Navarra", "ES23": "La Rioja", "ES24": "Aragón", "ES30": "Comunidad de Madrid",
    "ES41": "Castilla y León", "ES42": "Castilla-La Mancha", "ES43": "Extremadura", "ES51": "Cataluña",
    "ES52": "Comunidad Valenciana", "ES53": "Illes Balears", "ES61": "Andalucía", "ES62": "Región de Murcia",
    "ES63": "Ciudad Autónoma de Ceuta", "ES64": "Ciudad Autónoma de Melilla", "ES70": "Canarias",
}


def sector_legible(cpv: str | None) -> str:
    if not cpv or len(cpv) < 2:
        return "Sin clasificar"
    return CPV_DIVISIONES.get(cpv[:2], f"Otros (CPV {cpv[:2]})")


def ccaa_legible(nuts: str | None) -> str:
    if not nuts or len(nuts) < 4:
        return "España (sin especificar)"
    return CCAA_POR_NUTS2.get(nuts[:4], "España (otra zona)")


# --------------------------------------------------------------------------
# PLACSP: parseo CODICE
# --------------------------------------------------------------------------
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
}


def _text(el, path):
    f = el.find(path, NS)
    return f.text.strip() if f is not None and f.text else None


def _attr(el, path, attr):
    f = el.find(path, NS)
    return f.get(attr) if f is not None else None


def _all_text(el, path):
    return [e.text.strip() for e in el.findall(path, NS) if e.text and e.text.strip()]


def parse_entry(entry) -> dict | None:
    cfs = entry.find(".//cac-place-ext:ContractFolderStatus", NS)
    if cfs is None:
        return None
    estado = _text(cfs, "cbc-place-ext:ContractFolderStatusCode")
    if estado != "PUB":
        return None  # solo nos interesan las abiertas

    external_id = _text(entry, "atom:id")
    expediente = _text(cfs, "cbc:ContractFolderID")
    organo = _text(cfs, ".//cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name")
    proj = cfs.find(".//cac:ProcurementProject", NS)
    objeto = _text(proj, "cbc:Name") if proj is not None else None
    tipo_code = _text(proj, "cbc:TypeCode") if proj is not None else None
    titulo = _text(entry, "atom:title") or objeto
    importe = None
    if proj is not None:
        importe = _text(proj, "cac:BudgetAmount/cbc:TotalAmount") or _text(proj, "cac:BudgetAmount/cbc:EstimatedOverallContractAmount")
    cpv_codes = sorted(set(_all_text(cfs, ".//cbc:ItemClassificationCode")))
    ubicacion_nombre = _text(cfs, ".//cac:RealizedLocation/cbc:CountrySubentity")
    ubicacion_nuts = _text(cfs, ".//cac:RealizedLocation/cbc:CountrySubentityCode")
    plazo_fecha = _text(cfs, ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndDate")
    plazo_hora = _text(cfs, ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndTime")
    requisitos = _all_text(cfs, ".//cac:SpecificTendererRequirement/cbc:Description")
    solv_tec = _all_text(cfs, ".//cac:TechnicalEvaluationCriteria/cbc:Description")
    solv_eco = _all_text(cfs, ".//cac:FinancialEvaluationCriteria/cbc:Description")

    documentos = []
    for tag, categoria in (
        ("cac:LegalDocumentReference", "PCAP (pliego administrativo)"),
        ("cac:TechnicalDocumentReference", "PPT (pliego técnico)"),
        ("cac:AdditionalDocumentReference", "Anexo / documentación adicional"),
    ):
        for ref in cfs.findall(f".//{tag}", NS):
            nombre = _text(ref, "cbc:ID")
            uri = _text(ref, "cac:Attachment/cac:ExternalReference/cbc:URI")
            if uri:
                documentos.append({"categoria": categoria, "nombre": nombre or categoria, "url": uri})

    if not expediente and not titulo:
        return None

    try:
        importe_f = float(importe) if importe else None
    except ValueError:
        importe_f = None

    return {
        "fuente": "PLACSP",
        "external_id": external_id,
        "expediente": expediente,
        "titulo": titulo,
        "objeto": objeto,
        "organo": organo,
        "tipo_contrato_legible": TIPO_CONTRATO.get(tipo_code, tipo_code),
        "importe": importe_f,
        "sector": sector_legible(cpv_codes[0]) if cpv_codes else "Sin clasificar",
        "ccaa": ccaa_legible(ubicacion_nuts),
        "ubicacion_nombre": ubicacion_nombre,
        "estado": "PUB",
        "estado_legible": "Abierta (plazo de presentación en curso)",
        "plazo_fecha": plazo_fecha,
        "plazo_hora": plazo_hora,
        "requisitos": requisitos,
        "solvencia_tecnica": solv_tec,
        "solvencia_economica": solv_eco,
        "documentos": documentos,
        "detail_url": _attr(entry, "atom:link", "href"),
        "cpv_codes": cpv_codes,
    }


def next_link(xml_bytes: bytes) -> str | None:
    root = ET.fromstring(xml_bytes)
    self_href = None
    next_href = None
    for link in root.findall("atom:link", NS):
        if link.get("rel") == "self":
            self_href = link.get("href")
        if link.get("rel") == "next":
            next_href = link.get("href")
    if next_href and next_href != self_href:
        return next_href
    return None


def fetch_placsp(max_pages: int, ca_bundle: str) -> list[dict]:
    out = []
    url = FEED_URL
    for i in range(max_pages):
        resp = requests.get(url, headers=HEADERS, timeout=30, verify=ca_bundle)
        resp.raise_for_status()
        content = resp.content
        root = ET.fromstring(content)
        for entry in root.findall("atom:entry", NS):
            parsed = parse_entry(entry)
            if parsed:
                out.append(parsed)
        nxt = next_link(content)
        print(f"  página {i+1}: {len(out)} abiertas acumuladas", file=sys.stderr)
        if not nxt:
            break
        url = nxt
        time.sleep(0.4)
    return out


# --------------------------------------------------------------------------
# Bilbao / Open Data Euskadi
# --------------------------------------------------------------------------
def _to_float_es(s):
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def fetch_bilbao() -> list[dict]:
    try:
        resp = requests.get(
            "https://www.bilbao.eus/opendata/datos/licitaciones",
            params={"formato": "json", "estados": 3, "idioma": "es"},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[bilbao] no disponible: {exc}", file=sys.stderr)
        return []
    out = []
    for item in data.get("licitaciones", []):
        expediente = item.get("N_Expediente")
        if not expediente:
            continue
        area = item.get("Area_Municipal_promotora_del_Expediente")
        out.append(
            {
                "fuente": "Ayuntamiento de Bilbao",
                "external_id": f"bilbao-{expediente}",
                "expediente": expediente,
                "titulo": item.get("Objeto") or "(sin título)",
                "objeto": item.get("Objeto"),
                "organo": "Ayuntamiento de Bilbao" + (f" — {area}" if area else ""),
                "tipo_contrato_legible": item.get("Tipo_Contrato"),
                "importe": _to_float_es(item.get("Presupuesto_de_licitacion_IVA_Excluido")),
                "sector": "Sin clasificar (fuente municipal)",
                "ccaa": "País Vasco",
                "ubicacion_nombre": "Bilbao (Bizkaia)",
                "estado": "PUB",
                "estado_legible": "Abierta (plazo de presentación en curso)",
                "plazo_fecha": None,
                "plazo_hora": None,
                "requisitos": [],
                "solvencia_tecnica": [],
                "solvencia_economica": [],
                "documentos": [],
                "detail_url": "https://www.bilbao.eus/cs/Satellite/contratacionAdministrativa",
                "cpv_codes": [],
            }
        )
    return out


# --------------------------------------------------------------------------
# TendersGuru (terceros, best-effort)
# --------------------------------------------------------------------------
def fetch_tenders_guru(max_pages: int = 5) -> list[dict]:
    out = []
    try:
        for page in range(1, max_pages + 1):
            resp = requests.get(
                "https://tenders.guru/api/es/tenders", params={"page": page}, headers=HEADERS, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or data.get("data") or data.get("tenders") or []
            if not results:
                break
            for item in results:
                tid = item.get("id") or item.get("tender_id")
                title = item.get("title") or item.get("name")
                if not tid or not title:
                    continue
                out.append(
                    {
                        "fuente": "TendersGuru",
                        "external_id": f"tendersguru-{tid}",
                        "expediente": str(tid),
                        "titulo": title,
                        "objeto": item.get("description"),
                        "organo": item.get("buyer") or item.get("organization") or "No especificado",
                        "tipo_contrato_legible": item.get("type") or "No especificado",
                        "importe": item.get("value") or item.get("budget"),
                        "sector": item.get("category") or "Sin clasificar",
                        "ccaa": item.get("region") or "España (sin especificar)",
                        "ubicacion_nombre": item.get("location"),
                        "estado": "PUB",
                        "estado_legible": "Abierta (plazo de presentación en curso)",
                        "plazo_fecha": item.get("closing_date") or item.get("deadline"),
                        "plazo_hora": None,
                        "requisitos": [],
                        "solvencia_tecnica": [],
                        "solvencia_economica": [],
                        "documentos": [],
                        "detail_url": item.get("url") or f"https://tenders.guru/es/tender/{tid}",
                        "cpv_codes": [],
                    }
                )
            if not data.get("next") and len(results) < 20:
                break
    except Exception as exc:
        print(f"[tenders_guru] no disponible: {exc}", file=sys.stderr)
        return []
    return out


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=15)
    ap.add_argument("--out", type=Path, default=Path("licitaciones.json"))
    args = ap.parse_args()

    tmp_dir = args.out.resolve().parent
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ca_bundle = _ca_bundle(tmp_dir)

    print("Descargando PLACSP...", file=sys.stderr)
    registros = fetch_placsp(args.pages, ca_bundle)
    conteo = {"PLACSP": len(registros)}

    print("Descargando Bilbao...", file=sys.stderr)
    bilbao = fetch_bilbao()
    conteo["Ayuntamiento de Bilbao"] = len(bilbao)
    registros.extend(bilbao)

    print("Probando TendersGuru...", file=sys.stderr)
    tg = fetch_tenders_guru()
    conteo["TendersGuru"] = len(tg)
    registros.extend(tg)

    payload = {
        "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
        "total": len(registros),
        "por_fuente": conteo,
        "licitaciones": registros,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(f"\nExportado {len(registros)} licitaciones a {args.out}", file=sys.stderr)
    for f, n in conteo.items():
        print(f"  {f}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()
