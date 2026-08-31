"""
enemdu_mappings.py
==================
Catálogo semántico de ENEMDU: alias de variables, mapeos de códigos y
clasificadores de etiquetas.

Principio de diseño
-------------------
Los códigos **no se asumen a ciegas**. La estrategia es:

1. Si el diccionario XLSX del año trae etiquetas (código → texto), se usan esas
   etiquetas y se clasifican por patrón semántico (regex sobre el texto).
2. Sólo si el diccionario no está disponible o no es interpretable se aplica el
   mapeo *fallback* documentado abajo (formato ENEMDU 2021-2025 del INEC).

Cada resultado indica su procedencia (`diccionario` | `fallback`) para que la
auditoría deje constancia del supuesto aplicado.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 1. Alias de variables: nombre técnico INEC → nombre legible en Silver
# --------------------------------------------------------------------------- #
#: El orden importa: se toma el primer alias presente en el CSV del año.
COLUMN_ALIASES: Dict[str, List[str]] = {
    # Identificación y diseño muestral
    "anio":                 ["anio", "ano", "year", "periodo"],
    "mes":                  ["mes", "month"],
    "conglomerado":         ["conglomerado", "upm"],
    "vivienda":             ["vivienda", "nviv"],
    "hogar":                ["hogar", "nhog"],
    # OJO: en ENEMDU `p01` es *parentesco*, no el identificador de persona.
    "id_persona":           ["id_persona", "idpersona", "nper", "num_per", "persona"],
    "factor_expansion":     ["fexp", "fexp_anual", "factor_expansion", "peso"],
    # Geografía
    "codigo_ciudad":        ["ciudad", "codigo_ciudad", "canton"],
    "codigo_provincia":     ["provincia", "prov", "codigo_provincia"],
    "area_cod":             ["area", "area_geografica"],
    # Demografía
    "sexo_cod":             ["p02", "sexo", "p2"],
    "edad":                 ["p03", "edad", "p3"],
    "estado_civil_cod":     ["p04", "estado_civil"],
    "parentesco_cod":       ["p01", "parentesco"],
    # Educación
    "nivel_instruccion_cod": ["p10a", "nivel_instruccion", "nivelins", "nnivins"],
    "anios_aprobados":      ["p10b", "anio_aprobado", "grado_aprobado"],
    "asiste_clases_cod":    ["p07", "asiste"],
    # Mercado laboral
    "condicion_actividad_cod": ["condact", "condactn", "condicion_actividad"],
    "ocupacion_cod":        ["p41", "ocupacion", "ciuo"],
    "grupo_ocupacion_cod":  ["grupo1", "gruocu", "grupo_ocupacion"],
    "rama_cod":             ["p42", "rama", "ciiu"],
    "rama_agrupada_cod":    ["rama1", "rama_actividad"],
    "categoria_ocupacion_cod": ["p42a", "p42b", "categ_ocup", "categoria_ocupacion"],
    "sector_empleo_cod":    ["secemp", "sector_empleo", "sector"],
    "horas_trabajadas":     ["p51a", "totalhoras", "horastrab", "p24"],
    "ingreso_laboral":      ["ingrl", "ingreso_laboral", "ingreso"],
    "afiliacion_cod":       ["p05a", "afiliacion", "p05"],
    "empleo_informal_cod":  ["informal", "sectinf", "empleo_informal"],
}

#: Variables sin las cuales el caso de uso de empleabilidad no es viable.
REQUIRED_FOR_GOLD: Tuple[str, ...] = (
    "edad", "sexo_cod", "nivel_instruccion_cod", "condicion_actividad_cod",
)

# --------------------------------------------------------------------------- #
# 2. Mapeos fallback (formato INEC 2021-2025)
# --------------------------------------------------------------------------- #
FALLBACK_AREA: Dict[int, str] = {1: "Urbana", 2: "Rural"}

FALLBACK_SEXO: Dict[int, str] = {1: "Hombre", 2: "Mujer"}

FALLBACK_NIVEL_INSTRUCCION: Dict[int, str] = {
    1: "Ninguno",
    2: "Centro de alfabetización",
    3: "Jardín de infantes",
    4: "Primaria",
    5: "Educación Básica",
    6: "Secundaria",
    7: "Educación Media/Bachillerato",
    8: "Superior no universitaria",
    9: "Superior universitaria",
    10: "Post-grado",
}

FALLBACK_CONDACT: Dict[int, str] = {
    1: "Empleo adecuado/pleno",
    2: "Subempleo por insuficiencia de tiempo de trabajo",
    3: "Subempleo por insuficiencia de ingresos",
    4: "Otro empleo no pleno",
    5: "Empleo no remunerado",
    6: "Empleo no clasificado",
    7: "Desempleo abierto",
    8: "Desempleo oculto",
    9: "Población económicamente inactiva (PEI)",
    10: "Menor de 15 años",
}

#: CIUO-08, grandes grupos (primer dígito).
CIUO08_GRUPOS: Dict[int, str] = {
    0: "Ocupaciones militares",
    1: "Directores y gerentes",
    2: "Profesionales científicos e intelectuales",
    3: "Técnicos y profesionales de nivel medio",
    4: "Personal de apoyo administrativo",
    5: "Trabajadores de servicios y vendedores",
    6: "Agricultores y trabajadores calificados agropecuarios",
    7: "Oficiales, operarios y artesanos",
    8: "Operadores de instalaciones y máquinas",
    9: "Ocupaciones elementales",
}

#: Nivel de competencia CIUO-08 por gran grupo (1 = bajo … 4 = alto).
CIUO08_SKILL_LEVEL: Dict[int, int] = {
    1: 4, 2: 4, 3: 3, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 1, 0: 2,
}

#: Grandes grupos CIUO-08 que sí requieren formación superior (niveles 3-4).
GRUPOS_REQUIEREN_SUPERIOR: Tuple[int, ...] = (1, 2, 3)

#: CIIU-4, secciones (código agrupado ENEMDU `rama1` 1..21).
CIIU4_SECCIONES: Dict[int, str] = {
    1: "A. Agricultura, ganadería, silvicultura y pesca",
    2: "B. Explotación de minas y canteras",
    3: "C. Industrias manufactureras",
    4: "D. Suministro de electricidad y gas",
    5: "E. Suministro de agua y saneamiento",
    6: "F. Construcción",
    7: "G. Comercio al por mayor y menor",
    8: "H. Transporte y almacenamiento",
    9: "I. Alojamiento y servicios de comida",
    10: "J. Información y comunicación",
    11: "K. Actividades financieras y de seguros",
    12: "L. Actividades inmobiliarias",
    13: "M. Actividades profesionales, científicas y técnicas",
    14: "N. Actividades de servicios administrativos y de apoyo",
    15: "O. Administración pública y defensa",
    16: "P. Enseñanza",
    17: "Q. Salud humana y asistencia social",
    18: "R. Artes, entretenimiento y recreación",
    19: "S. Otras actividades de servicios",
    20: "T. Hogares como empleadores",
    21: "U. Organizaciones extraterritoriales",
}

#: Provincias del Ecuador (DPA-INEC).
PROVINCIAS_EC: Dict[int, str] = {
    1: "Azuay", 2: "Bolívar", 3: "Cañar", 4: "Carchi", 5: "Cotopaxi",
    6: "Chimborazo", 7: "El Oro", 8: "Esmeraldas", 9: "Guayas", 10: "Imbabura",
    11: "Loja", 12: "Los Ríos", 13: "Manabí", 14: "Morona Santiago", 15: "Napo",
    16: "Pastaza", 17: "Pichincha", 18: "Tungurahua", 19: "Zamora Chinchipe",
    20: "Galápagos", 21: "Sucumbíos", 22: "Orellana", 23: "Santo Domingo de los Tsáchilas",
    24: "Santa Elena", 90: "Zonas no delimitadas",
}

# --------------------------------------------------------------------------- #
# 3. Clasificadores semánticos sobre etiquetas del diccionario
# --------------------------------------------------------------------------- #
#: (categoría, patrón). El orden es relevante: se evalúa de arriba a abajo.
EDU_PATTERNS: List[Tuple[str, str]] = [
    ("Post-grado", r"post\s*-?\s*grado|maestr|doctor|phd|especializac"),
    ("Superior universitaria", r"superior\s+universitar|universitar"),
    ("Superior no universitaria", r"superior\s+no\s+universitar|tecnolog|tecnic\w*\s+superior"),
    ("Educación Media/Bachillerato", r"media|bachiller"),
    ("Secundaria", r"secundar"),
    ("Educación Básica", r"b[aá]sic"),
    ("Primaria", r"primar"),
    ("Jardín de infantes", r"jard[ií]n|preescolar|inicial"),
    ("Centro de alfabetización", r"alfabetiz"),
    ("Ninguno", r"ningun|sin\s+instrucc"),
]

CONDACT_PATTERNS: List[Tuple[str, str]] = [
    ("Empleo adecuado/pleno", r"adecuad|pleno"),
    ("Subempleo por insuficiencia de tiempo de trabajo", r"subempleo.*tiempo|tiempo.*subempleo"),
    ("Subempleo por insuficiencia de ingresos", r"subempleo.*ingres|ingres.*subempleo"),
    ("Otro empleo no pleno", r"otro\s+empleo|no\s+pleno"),
    ("Empleo no remunerado", r"no\s+remunerad"),
    ("Empleo no clasificado", r"no\s+clasificad"),
    ("Desempleo abierto", r"desempleo\s+abierto"),
    ("Desempleo oculto", r"desempleo\s+oculto"),
    ("Población económicamente inactiva (PEI)", r"inactiv|pei"),
    ("Menor de 15 años", r"menor(es)?\s+de\s+1[05]"),
]

#: Categorías de nivel educativo consideradas "graduado universitario".
NIVELES_SUPERIOR: Tuple[str, ...] = ("Superior universitaria", "Post-grado")

#: Categorías de `condicion_actividad` que implican estar ocupado.
CATEGORIAS_OCUPADO: Tuple[str, ...] = (
    "Empleo adecuado/pleno",
    "Subempleo por insuficiencia de tiempo de trabajo",
    "Subempleo por insuficiencia de ingresos",
    "Otro empleo no pleno",
    "Empleo no remunerado",
    "Empleo no clasificado",
)
CATEGORIAS_DESEMPLEADO: Tuple[str, ...] = ("Desempleo abierto", "Desempleo oculto")
CATEGORIAS_SUBEMPLEO: Tuple[str, ...] = (
    "Subempleo por insuficiencia de tiempo de trabajo",
    "Subempleo por insuficiencia de ingresos",
)


def classify_labels(labels: Dict[str, str],
                    patterns: List[Tuple[str, str]]) -> Dict[int, str]:
    """Traduce etiquetas del diccionario a categorías canónicas por regex.

    Ejemplo: {'9': 'Superior Universitario'} → {9: 'Superior universitaria'}
    Los códigos cuya etiqueta no coincide con ningún patrón se descartan
    (quedarán como NaN en Silver y se reportan en la auditoría).
    """
    out: Dict[int, str] = {}
    for code, text in (labels or {}).items():
        try:
            code_int = int(code)
        except (TypeError, ValueError):
            continue
        norm = str(text).lower()
        for canon, pattern in patterns:
            if re.search(pattern, norm):
                out[code_int] = canon
                break
    return out


def resolve_map(labels: Optional[Dict[str, str]],
                patterns: Optional[List[Tuple[str, str]]],
                fallback: Dict[int, str]) -> Tuple[Dict[int, str], str]:
    """Devuelve (mapa código→categoría, procedencia).

    Prioriza el diccionario del año; si no alcanza al menos el 60 % de los
    códigos del fallback, usa el fallback documentado.
    """
    if labels and patterns:
        derived = classify_labels(labels, patterns)
        if len(derived) >= max(3, int(0.6 * len(fallback))):
            return derived, "diccionario"
    if labels and not patterns:
        direct = {}
        for code, text in labels.items():
            try:
                direct[int(code)] = str(text).strip()
            except (TypeError, ValueError):
                continue
        if direct:
            return direct, "diccionario"
    return dict(fallback), "fallback"


def ciuo_major_group(value) -> Optional[int]:
    """Obtiene el gran grupo CIUO-08 desde un código de 1 a 4 dígitos."""
    try:
        code = int(float(value))
    except (TypeError, ValueError):
        return None
    if code < 0:
        return None
    text = str(code)
    if len(text) > 1:            # 4/3/2 dígitos → primer dígito
        code = int(text[0])
    if code == 10:               # algunos años codifican militares como 10
        code = 0
    return code if 0 <= code <= 9 else None
