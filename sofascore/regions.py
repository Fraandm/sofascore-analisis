"""Regiones y competiciones admitidas por el analizador de forma.

El programa admite competiciones profesionales de Europa, Sudamérica y las
competiciones oficiales de selecciones absolutas. Los IDs de categoría son los
que usa SofaScore en ``/sport/football/categories/all`` y se verificaron en
noviembre de 2026.
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

# Categorías de países europeos (senior). Se excluyen las categorías
# "Amateur" para no mezclar competiciones no profesionales.
EUROPE_CATEGORY_IDS = frozenset(
    {
        1,    # England
        32,   # Spain
        30,   # Germany
        31,   # Italy
        7,    # France
        44,   # Portugal
        35,   # Netherlands
        33,   # Belgium
        46,   # Turkey
        22,   # Scotland
        130,  # Northern Ireland
        131,  # Wales
        51,   # Ireland
        17,   # Austria
        25,   # Switzerland
        67,   # Greece
        102,  # Cyprus
        66,   # Israel
        5,    # Norway
        9,    # Sweden
        19,   # Finland
        10,   # Iceland
        8,    # Denmark
        47,   # Poland
        77,   # Romania
        279,  # Moldova
        86,   # Ukraine
        21,   # Russia
        91,   # Belarus
        11,   # Hungary
        18,   # Czech Republic
        23,   # Slovakia
        24,   # Slovenia
        14,   # Croatia
        152,  # Serbia
        158,  # Bosnia & Herzegovina
        78,   # Bulgaria
        257,  # Albania
        159,  # North Macedonia
        1112, # Kosovo
        386,  # Montenegro
        134,  # Malta
        197,  # Luxembourg
        512,  # Liechtenstein
        376,  # Andorra
        387,  # San Marino
        938,  # Gibraltar
        201,  # Faroe Islands
        1465, # Europe (competiciones continentales)
    }
)

SOUTH_AMERICA_CATEGORY_IDS = frozenset(
    {
        48,   # Argentina
        379,  # Bolivia
        13,   # Brazil
        49,   # Chile
        274,  # Colombia
        165,  # Ecuador
        280,  # Paraguay
        20,   # Peru
        57,   # Uruguay
        281,  # Venezuela
        1470, # South America (Libertadores, Sudamericana...)
    }
)

# Competiciones oficiales de selecciones masculinas absolutas. También se
# incluye el torneo de amistosos 851 para poder analizarlos en la interfaz,
# pero el recolector y el entrenamiento los excluyen explícitamente.
NATIONAL_TOURNAMENT_IDS = frozenset(
    {
        10783,  # UEFA Nations League
        133,    # Copa América
        16,     # Copa Mundial de la FIFA
        11,     # Eliminatorias Mundial · UEFA
        295,    # Eliminatorias Mundial · CONMEBOL
        13,     # Eliminatorias Mundial · CAF
        14,     # Eliminatorias Mundial · CONCACAF
        308,    # Eliminatorias Mundial · AFC
        309,    # Eliminatorias Mundial · OFC
        1,      # Eurocopa
        27,     # Clasificación Eurocopa
        28,     # Clasificación Copa Asiática
        1848,   # Clasificación Copa Africana
        140,    # Copa Oro CONCACAF
        270,    # Copa Africana de Naciones
        246,    # Copa Asiática
        14100,  # CONCACAF Nations League
        22716,  # OFC Men's Nations Cup
        18654,  # Finalissima
        10618,  # Repesca intercontinental al Mundial
        851,    # Amistosos internacionales (solo análisis)
    }
)

# Amistosos internacionales: fuera del dataset y del entrenamiento.
FRIENDLY_TOURNAMENT_IDS = frozenset({851, 852})

REGION_EUROPE = "Europa"
REGION_SOUTH_AMERICA = "Sudamérica"
REGION_NATIONAL = "Selecciones"

REGION_ALIASES = {
    "ambas": "ambas",
    "ambos": "ambas",
    "todas": "ambas",
    "todo": "ambas",
    "europa": "europa",
    "europe": "europa",
    "sudamerica": "sudamerica",
    "sud america": "sudamerica",
    "south america": "sudamerica",
    "selecciones": "selecciones",
    "seleccion": "selecciones",
    "selecciones absolutas": "selecciones",
    "nacional": "selecciones",
    "nacionales": "selecciones",
    "internacional": "selecciones",
    "internacionales": "selecciones",
    "national": "selecciones",
    "national teams": "selecciones",
}


def _plain(value: Any) -> str:
    text = str(value or "").strip().casefold()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_region(value: Optional[str]) -> str:
    """Devuelve ``ambas``, ``europa``, ``sudamerica`` o ``selecciones``."""
    if value is None:
        return "ambas"
    return REGION_ALIASES.get(_plain(value), "ambas")


def region_for_category(category_id: Any) -> Optional[str]:
    """Región de una categoría de SofaScore (o ``None`` si no aplica)."""
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return None
    if category_id in EUROPE_CATEGORY_IDS:
        return REGION_EUROPE
    if category_id in SOUTH_AMERICA_CATEGORY_IDS:
        return REGION_SOUTH_AMERICA
    return None


def region_for_tournament(
    tournament_id: Any, category_id: Any = None
) -> Optional[str]:
    """Región de un torneo; las selecciones tienen prioridad sobre la categoría."""
    try:
        tournament_id = int(tournament_id)
    except (TypeError, ValueError):
        tournament_id = None
    if tournament_id in NATIONAL_TOURNAMENT_IDS:
        return REGION_NATIONAL
    return region_for_category(category_id)


def _team_is_national(team: Any) -> bool:
    return isinstance(team, dict) and bool(team.get("national"))


def is_national_match(match: Dict[str, Any]) -> bool:
    """Indica si el partido enfrenta a selecciones (incluidos amistosos)."""
    match = match or {}
    tournament = match.get("tournament") or {}
    try:
        tournament_id = int(tournament.get("id"))
    except (TypeError, ValueError):
        tournament_id = None
    if tournament_id in NATIONAL_TOURNAMENT_IDS:
        return True
    return _team_is_national(match.get("home_team")) or _team_is_national(
        match.get("away_team")
    )


def region_for_match(match: Dict[str, Any]) -> Optional[str]:
    """Región de un partido normalizado."""
    match = match or {}
    tournament = match.get("tournament") or {}
    tournament_id = tournament.get("id")
    category_id = tournament.get("category_id")
    if tournament_id is not None:
        region = region_for_tournament(tournament_id, category_id)
        if region is not None:
            return region
    if is_national_match(match):
        return REGION_NATIONAL
    return region_for_category(category_id)


def match_in_region(match: Dict[str, Any], region: str = "ambas") -> bool:
    wanted = normalize_region(region)
    match_region = region_for_match(match)
    if match_region is None:
        return False
    if wanted == "ambas":
        return True
    return normalize_region(match_region) == wanted
