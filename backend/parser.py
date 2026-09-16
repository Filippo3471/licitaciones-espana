"""Parseo de entradas CODICE (formato XML de la Plataforma de Contratación del
Sector Público - PLACSP) a un diccionario plano listo para guardar en SQLite.

Referencia del formato: Manual OpenPLACSP (Dirección General del Patrimonio
del Estado) y especificación CODICE 2.07 del Ministerio de Hacienda.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
}


def _text(el, path):
    found = el.find(path, NS)
    return found.text.strip() if found is not None and found.text else None


def _attr(el, path, attr):
    found = el.find(path, NS)
    return found.get(attr) if found is not None else None


def _all_text(el, path):
    return [e.text.strip() for e in el.findall(path, NS) if e.text and e.text.strip()]


def parse_entry(entry: ET.Element) -> dict | None:
    """Convierte un <entry> del feed ATOM/CODICE en un dict. Devuelve None si
    la entrada no tiene los datos mínimos (p.ej. una tombstone de borrado)."""
    cfs = entry.find(".//cac-place-ext:ContractFolderStatus", NS)
    if cfs is None:
        return None

    external_id = _text(entry, "atom:id")
    detail_url = _attr(entry, "atom:link", "href")
    updated = _text(entry, "atom:updated")
    expediente = _text(cfs, "cbc:ContractFolderID")
    estado = _attr(cfs, "cbc-place-ext:ContractFolderStatusCode", "") or _text(
        cfs, "cbc-place-ext:ContractFolderStatusCode"
    )

    organo = _text(cfs, ".//cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name")
    tipo_organo = _attr(
        cfs, ".//cac-place-ext:LocatedContractingParty/cbc:ContractingPartyTypeCode", "listURI"
    )
    tipo_organo_code = _text(cfs, ".//cac-place-ext:LocatedContractingParty/cbc:ContractingPartyTypeCode")

    proj = cfs.find(".//cac:ProcurementProject", NS)
    objeto = _text(proj, "cbc:Name") if proj is not None else None
    tipo_contrato_code = _text(proj, "cbc:TypeCode") if proj is not None else None

    titulo = _text(entry, "atom:title") or objeto

    importe = None
    if proj is not None:
        importe = _text(proj, "cac:BudgetAmount/cbc:TotalAmount") or _text(
            proj, "cac:BudgetAmount/cbc:EstimatedOverallContractAmount"
        )

    cpv_codes = sorted(set(_all_text(cfs, ".//cbc:ItemClassificationCode")))

    ubicacion_nombre = _text(cfs, ".//cac:RealizedLocation/cbc:CountrySubentity")
    ubicacion_nuts = _text(cfs, ".//cac:RealizedLocation/cbc:CountrySubentityCode")

    plazo_fecha = _text(cfs, ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndDate")
    plazo_hora = _text(cfs, ".//cac:TenderSubmissionDeadlinePeriod/cbc:EndTime")

    requisitos = _all_text(cfs, ".//cac:SpecificTendererRequirement/cbc:Description")
    solvencia_tecnica = _all_text(cfs, ".//cac:TechnicalEvaluationCriteria/cbc:Description")
    solvencia_economica = _all_text(cfs, ".//cac:FinancialEvaluationCriteria/cbc:Description")

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

    pyme_adjudicado = _text(cfs, ".//cbc:SMEAwardedIndicator")

    if not expediente and not titulo:
        return None

    return {
        "external_id": external_id,
        "expediente": expediente,
        "detail_url": detail_url,
        "updated": updated,
        "estado": estado,
        "titulo": titulo,
        "objeto": objeto,
        "organo": organo,
        "tipo_organo_code": tipo_organo_code,
        "tipo_contrato_code": tipo_contrato_code,
        "importe": importe,
        "cpv_codes": cpv_codes,
        "ubicacion_nombre": ubicacion_nombre,
        "ubicacion_nuts": ubicacion_nuts,
        "plazo_fecha": plazo_fecha,
        "plazo_hora": plazo_hora,
        "requisitos": requisitos,
        "solvencia_tecnica": solvencia_tecnica,
        "solvencia_economica": solvencia_economica,
        "documentos": documentos,
        "pyme_adjudicado": pyme_adjudicado,
    }


def iter_entries(xml_bytes: bytes):
    """Itera sobre las <entry> de una página del feed y produce dicts parseados."""
    root = ET.fromstring(xml_bytes)
    for entry in root.findall("atom:entry", NS):
        parsed = parse_entry(entry)
        if parsed:
            yield parsed


def next_link(xml_bytes: bytes) -> str | None:
    root = ET.fromstring(xml_bytes)
    for link in root.findall("atom:link", NS):
        if link.get("rel") == "next":
            href = link.get("href")
            self_href = None
            for l2 in root.findall("atom:link", NS):
                if l2.get("rel") == "self":
                    self_href = l2.get("href")
            if href and href != self_href:
                return href
    return None
