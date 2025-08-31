"""Pomocné nástroje na streamovanie a validáciu CSV."""

from __future__ import annotations

import csv
import logging
from collections import deque
from collections.abc import Iterable, Iterator, MutableSet
from dataclasses import dataclass
from typing import TypeVar
import _csv

from .validators import (
    ValidationError,
    validate_age,
    validate_banner_id,
    validate_cookie,
    validate_name,
)

logger = logging.getLogger(__name__)

REQUIRED_HEADERS = {"name", "age", "banner_id", "cookie"}


def _read_csv(csv_path: str) -> tuple[list[str], Iterator[dict[str, str]]]:
    """Vráti hlavičky a generátor orezaných riadkov zo súboru ``csv_path``."""

    f = open(csv_path, encoding="utf-8-sig", newline="")
    sample = f.read(2048)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(f, dialect=dialect)
    headers = [h.strip() for h in (reader.fieldnames or [])]
    if len(headers) != len(set(headers)):
        f.close()
        raise ValueError("duplicate headers detected")

    def row_iter() -> Iterator[dict[str, str]]:
        try:
            for row in reader:
                trimmed = {k.strip(): (v or "").strip() for k, v in row.items()}
                if all(v == "" for v in trimmed.values()):
                    continue
                yield trimmed
        finally:
            f.close()

    return headers, row_iter()


class CSVProcessor(Iterator[dict[str, int | str]]):
    """Iteruje cez platné riadky zo súboru CSV.

    Neplatné riadky sa preskočia a zalogujú s číslom riadku a dôvodom.
    Ak je zadaný ``error_writer``, neplatné riadky sa zapíšu do
    daného CSV zapisovača so stĺpcami ``name, age, banner_id, cookie, error``.
    Po iterácii atribút ``invalid_rows`` obsahuje počet preskočených záznamov.
    """

    def __init__(
        self,
        csv_path: str,
        min_age: int,
        max_age: int,
        error_writer: _csv._writer | None = None,
    ) -> None:
        headers, self._rows = _read_csv(csv_path)
        if not REQUIRED_HEADERS.issubset(set(headers)):
            raise ValueError(f"CSV must contain headers: {sorted(REQUIRED_HEADERS)}")
        self.min_age = min_age
        self.max_age = max_age
        self.invalid_rows = 0
        self._error_writer = error_writer
        self._row_iter = self._validate_rows()

    def __iter__(self) -> "CSVProcessor":
        return self

    def __next__(self) -> dict[str, int | str]:
        return next(self._row_iter)

    def _validate_rows(self) -> Iterator[dict[str, int | str]]:
        for idx, row in enumerate(self._rows, start=1):
            try:
                yield {
                    "name": validate_name(row.get("name", "")),
                    "age": validate_age(row.get("age", ""), self.min_age, self.max_age),
                    "banner_id": validate_banner_id(row.get("banner_id", "")),
                    "cookie": validate_cookie(row.get("cookie", "")),
                }
            except ValidationError as exc:
                self.invalid_rows += 1
                logger.warning(
                    "invalid_row",
                    extra={
                        "event": "invalid_row",
                        "row_id": idx,
                        "reason": str(exc),
                    },
                )
                if self._error_writer is not None:
                    self._error_writer.writerow(
                        [
                            row.get("name", ""),
                            row.get("age", ""),
                            row.get("banner_id", ""),
                            row.get("cookie", ""),
                            str(exc),
                        ]
                    )


T = TypeVar("T")


def chunk(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Vypúšťa zoznamy najviac ``size`` položiek z ``iterable``."""

    if size <= 0:
        raise ValueError("size must be > 0")
    batch: list[T] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


@dataclass
class ParseStats:
    """Štatistiky behu pri spracovaní CSV súboru."""

    valid: int = 0
    invalid: int = 0
    unique: int = 0


def parse_csv(
    csv_path: str,
    min_age: int,
    max_age: int,
    *,
    dedup_window: int | None = None,
    store: MutableSet[tuple[str, int]] | None = None,
    error_writer: _csv._writer | None = None,
) -> tuple[Iterator[dict[str, int | str]], ParseStats]:
    """Spracuje ``csv_path`` a postupne vracia unikátne platné riadky.

    Parametre
    ---------
    csv_path:
        Cesta k CSV súboru na spracovanie.
    dedup_window:
        Maximálny počet dvojíc (cookie, banner_id) zapamätaných
        pri deduplikácii. ``None`` ponechá všetky doteraz videné páry,
        čo môže neobmedzene rásť. Pri nastavení okna sa najstaršie
        záznamy po prekročení limitu odstránia.
    store:
        Voliteľná externá množina použitá na uloženie stavu deduplikácie
        medzi behmi. Ak je zadaná spolu s ``dedup_window``, záznamy
        odstránené z okna sa vymažú aj z ``store``.
    error_writer:
        Voliteľný CSV zapisovač pre neplatné riadky.

    Návratové hodnoty
    -----------------
    tuple
        ``(iterator, stats)`` kde ``iterator`` lenivo vracia unikátne platné
        riadky a ``stats`` počas iterácie počíta počty platných,
        neplatných a unikátnych riadkov.
    """

    processor = CSVProcessor(csv_path, min_age, max_age, error_writer)
    stats = ParseStats()
    seen: MutableSet[tuple[str, int]] = store or set()
    order: deque[tuple[str, int]] | None = deque() if dedup_window is not None else None

    def row_iter() -> Iterator[dict[str, int | str]]:
        for row in processor:
            stats.valid += 1
            cookie = str(row["cookie"])
            banner = int(row["banner_id"])
            key = (cookie, banner)
            if key in seen:
                continue
            seen.add(key)
            if order is not None:
                order.append(key)
                if dedup_window is not None and len(order) > dedup_window:
                    old = order.popleft()
                    seen.discard(old)
            stats.unique += 1
            yield row
        stats.invalid = processor.invalid_rows

    return row_iter(), stats


__all__ = ["CSVProcessor", "chunk", "REQUIRED_HEADERS", "parse_csv", "ParseStats"]
