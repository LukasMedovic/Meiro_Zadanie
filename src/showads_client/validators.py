"""Validačné nástroje vyhadzujúce špecifické výnimky."""

from __future__ import annotations

from typing import Any
import uuid


class ValidationError(Exception):
    """Základná trieda pre validačné chyby."""


class InvalidNameError(ValidationError):
    """Vstup ``name`` neprešiel validáciou."""


class InvalidAgeError(ValidationError):
    """Vstup ``age`` neprešiel validáciou."""


class InvalidBannerIdError(ValidationError):
    """Vstup ``banner_id`` neprešiel validáciou."""


class InvalidCookieError(ValidationError):
    """Vstup ``cookie`` neprešiel validáciou."""


def validate_name(name: Any) -> str:
    """Vráti orezaný ``name`` alebo vyhodí :class:`InvalidNameError`."""

    if not isinstance(name, str):
        raise InvalidNameError("name must be a string")
    s = name.strip()
    if not s:
        raise InvalidNameError("name cannot be empty")
    if not all(ch.isalpha() or ch.isspace() for ch in s):
        raise InvalidNameError("name contains invalid characters")
    return s


def validate_age(age: Any, min_age: int, max_age: int) -> int:
    """Vráti celé číslo ``age`` v rozsahu ``[min_age, max_age]`` alebo vyhodí výnimku."""

    try:
        a = int(str(age).strip())
    except Exception as exc:  # pragma: no cover - defensive
        raise InvalidAgeError("age must be an integer") from exc
    if not (min_age <= a <= max_age):
        raise InvalidAgeError(f"age {a} out of range {min_age}-{max_age}")
    return a


def validate_banner_id(banner_id: Any) -> int:
    """Vráti celé číslo ``banner_id`` v rozsahu 0..99 alebo vyhodí výnimku."""

    try:
        b = int(str(banner_id).strip())
    except Exception as exc:  # pragma: no cover - defensive
        raise InvalidBannerIdError("banner_id must be an integer") from exc
    if not (0 <= b <= 99):
        raise InvalidBannerIdError("banner_id out of range 0-99")
    return b


def validate_cookie(cookie: Any) -> str:
    """Vráti ``cookie`` ak ide o platný reťazec UUID, inak vyhodí výnimku."""

    try:
        uuid.UUID(str(cookie))
    except Exception as exc:  # pragma: no cover - defensive
        raise InvalidCookieError("cookie must be a valid UUID") from exc
    return str(cookie)


__all__ = [
    "ValidationError",
    "InvalidNameError",
    "InvalidAgeError",
    "InvalidBannerIdError",
    "InvalidCookieError",
    "validate_name",
    "validate_age",
    "validate_banner_id",
    "validate_cookie",
]
