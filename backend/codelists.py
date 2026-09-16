"""Tablas de códigos oficiales de CODICE/PLACSP traducidos a texto legible."""

ESTADO = {
    "PRE": "Anuncio previo",
    "PUB": "Abierta (plazo de presentación en curso)",
    "EV": "En evaluación",
    "ADJ": "Adjudicada",
    "RES": "Resuelta / formalizada",
    "ANUL": "Anulada",
    "DES": "Desierta",
    "PRE_UNCONVENED": "No convocada",
}

TIPO_CONTRATO = {
    "1": "Suministros",
    "2": "Servicios",
    "3": "Obras",
    "21": "Gestión de servicios públicos",
    "31": "Concesión de servicios",
    "32": "Concesión de obras",
}

TIPO_ORGANO = {
    "1": "Administración General del Estado",
    "2": "Administración Autonómica",
    "3": "Administración Local",
    "4": "Universidad pública",
    "5": "Organismo público",
    "6": "Sector público institucional",
    "8": "Otros",
}


def estado_legible(codigo: str) -> str:
    return ESTADO.get(codigo, codigo or "Desconocido")


def tipo_contrato_legible(codigo: str) -> str:
    return TIPO_CONTRATO.get(codigo, f"Otro ({codigo})" if codigo else "No especificado")


def tipo_organo_legible(codigo: str) -> str:
    return TIPO_ORGANO.get(codigo, codigo or "")
