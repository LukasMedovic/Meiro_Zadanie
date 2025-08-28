"""Validatory pre meno, vek a banner_id

Poznamky:
- isalpha() pokryva unicode pismena
- Zamer je konzervativny: povolujeme len pismena, medzery a hyphen '-'.
"""

from typing import Any


def is_valid_name(name: str) -> bool:
    """Overi, ci je meno platne.

    Pravidla:
      - vstup je string
      - po orezani bielych znakov nie je prazdny
      - obsahuje len pismena, medzery alebo hyphen '-'
    """
    if not isinstance(name, str):
        return False
    s = name.strip()
    if not s:
        return False
    # Konzervativne: unicode pismena, medzery, hyphen
    return all(ch.isalpha() or ch.isspace() or ch == "-" for ch in s)


def is_valid_age(age: Any, min_age: int, max_age: int) -> bool:
    """Overi vek voci intervalu [min_age, max_age]."""
    try:
        a = int(age)
    except Exception:
        return False
    return min_age <= a <= max_age


def is_valid_banner_id(banner_id: Any) -> bool:
    """Overi banner_id, musi byt integer v rozsahu 0..99 (vratane)."""
    try:
        b = int(banner_id)
    except Exception:
        return False
    return 0 <= b <= 99
