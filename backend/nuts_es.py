"""Comunidades Autónomas por prefijo NUTS-2 (España, revisión NUTS 2021)."""

CCAA_POR_NUTS2 = {
    "ES11": "Galicia",
    "ES12": "Principado de Asturias",
    "ES13": "Cantabria",
    "ES21": "País Vasco",
    "ES22": "Comunidad Foral de Navarra",
    "ES23": "La Rioja",
    "ES24": "Aragón",
    "ES30": "Comunidad de Madrid",
    "ES41": "Castilla y León",
    "ES42": "Castilla-La Mancha",
    "ES43": "Extremadura",
    "ES51": "Cataluña",
    "ES52": "Comunidad Valenciana",
    "ES53": "Illes Balears",
    "ES61": "Andalucía",
    "ES62": "Región de Murcia",
    "ES63": "Ciudad Autónoma de Ceuta",
    "ES64": "Ciudad Autónoma de Melilla",
    "ES70": "Canarias",
}


def ccaa_legible(nuts_code: str) -> str:
    if not nuts_code or len(nuts_code) < 4:
        return "España (sin especificar)"
    if nuts_code[:4] == "ES70":
        return "Canarias"
    return CCAA_POR_NUTS2.get(nuts_code[:4], "España (otra zona)")
