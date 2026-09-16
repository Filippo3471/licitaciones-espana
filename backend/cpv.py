"""Tabla de divisiones CPV (2 dígitos) -> sector, para clasificar 'a qué tipo de
empresa' le interesa la licitación. El vocabulario CPV completo tiene miles de
códigos; aquí usamos solo el nivel de división (los 2 primeros dígitos), que es
estable y oficial (Reglamento CE 213/2008 y sus actualizaciones)."""

DIVISIONES = {
    "03": "Agricultura, ganadería, pesca, silvicultura",
    "09": "Productos petrolíferos, combustibles, electricidad y energía",
    "14": "Minería y minerales",
    "15": "Alimentación, bebidas, tabaco",
    "16": "Maquinaria agrícola",
    "18": "Prendas de vestir, calzado",
    "19": "Cuero y textil",
    "22": "Impresión y artes gráficas",
    "24": "Productos químicos",
    "30": "Máquinas de oficina, informática",
    "31": "Maquinaria y aparatos eléctricos",
    "32": "Equipos de radio, TV, comunicaciones",
    "33": "Equipos médicos, farmacia, cosmética",
    "34": "Vehículos, transporte",
    "35": "Equipos de seguridad, defensa",
    "37": "Instrumentos musicales, deportivos, juegos",
    "38": "Equipos de laboratorio, óptica, precisión",
    "39": "Mobiliario, artículos del hogar, limpieza",
    "41": "Agua",
    "42": "Maquinaria industrial",
    "43": "Maquinaria de minería, construcción",
    "44": "Materiales de construcción",
    "45": "Construcción y obra civil",
    "48": "Paquetes de software y sistemas de información",
    "50": "Servicios de reparación y mantenimiento",
    "51": "Servicios de instalación",
    "55": "Servicios de hostelería y restauración",
    "60": "Servicios de transporte",
    "63": "Servicios de apoyo al transporte, agencias de viaje",
    "64": "Servicios postales y de telecomunicaciones",
    "65": "Servicios públicos (agua, energía)",
    "66": "Servicios financieros y de seguros",
    "70": "Servicios inmobiliarios",
    "71": "Servicios de arquitectura, ingeniería y construcción",
    "72": "Servicios de tecnologías de la información (TI)",
    "73": "Servicios de investigación y desarrollo (I+D)",
    "75": "Servicios de administración pública y defensa",
    "76": "Servicios relacionados con el sector del petróleo y gas",
    "77": "Servicios agrícolas, forestales, jardinería",
    "79": "Servicios empresariales: publicidad, limpieza, consultoría, seguridad",
    "80": "Servicios de educación y formación",
    "85": "Servicios de salud y acción social",
    "90": "Servicios medioambientales, saneamiento, residuos",
    "92": "Servicios recreativos, culturales y deportivos",
    "98": "Otros servicios comunitarios, sociales y personales",
}


def sector_legible(cpv_code: str) -> str:
    if not cpv_code or len(cpv_code) < 2:
        return "Sin clasificar"
    return DIVISIONES.get(cpv_code[:2], f"Otros (CPV {cpv_code[:2]})")
