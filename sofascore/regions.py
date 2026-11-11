"""Regiones y competiciones admitidas por el analizador de forma.

El programa se centra en competiciones profesionales de Europa y
Sudamérica. Los IDs de categoría son los que usa SofaScore en
``/sport/football/categories/all`` y se verificaron en noviembre de 2026.
"""

from __future__ import annotations

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

REGION_EUROPE = "Europa"
REGION_SOUTH_AMERICA = "Sudamérica"

REGION_ALIASES = {
    "ambas": "ambas",
    "ambos": "ambas",
    "todas": "ambas",
    "europa": "europa",
    "europe": "europa",
    "sudamerica": "sudamerica",
    "sudamérica": "sudamerica",
    "sud america": "sudamerica",
    "south america": "sudamerica",
}


def normalize_region(value: Optional[str]) -> str:
    """Devuelve ``ambas``, ``europa`` o ``sudamerica``."""
    if value is None:
        return "ambas"
    key = str(value).strip().casefold()
    if key in REGION_ALIASES:
        return REGION_ALIASES[key]
    # Acepta nombres con tilde/espacios sin depender de normalize para
    # evitar un import circular.
    plain = (
        key.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return REGION_ALIASES.get(plain, "ambas")


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


def region_for_match(match: Dict[str, Any]) -> Optional[str]:
    """Región de un partido normalizado."""
    tournament = (match or {}).get("tournament") or {}
    return region_for_category(tournament.get("category_id"))


def match_in_region(match: Dict[str, Any], region: str = "ambas") -> bool:
    wanted = normalize_region(region)
    match_region = region_for_match(match)
    if match_region is None:
        return False
    if wanted == "ambas":
        return True
    return normalize_region(match_region) == wanted
