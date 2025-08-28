"""CLI rozhranie pre ShowAds konektor

Prikazy:
  - validate <csv_path>: overi CSV a vypise sumar (bez siete)
  - send <csv_path>: validuje a (zatial) stubom "odosle" batch-e
"""

import csv
import sys
import json
import click

from .config import settings
from .validators import is_valid_name, is_valid_age, is_valid_banner_id
from .batching import chunked
from .api_client import ShowAdsClient


@click.group(help="ShowAds CSV -> API connector (skeleton)")
def main():
    """Vstupny bod CLI (click group)."""
    pass


@main.command("validate")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=str))
def validate_cmd(csv_path: str):
    """Validacia CSV a sumarizacia vysledkov (bez sietovej komunikacie).

    Ocekavane hlavicky: name, age, banner_id
    Vystup: JSON {"valid": X, "invalid": Y}
    Exit kody:
      - 0: OK
      - 2: chyba hlaviciek
    """
    valid = 0
    invalid = 0

    # Otvorime CSV v UTF-8; ak chyba hlavicka, skonci s chybou (exit 2)
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"name", "age", "banner_id"}
        if not required.issubset(reader.fieldnames or []):
            click.echo(f"ERROR: CSV must contain headers: {sorted(required)}", err=True)
            sys.exit(2)

        # Prechadzame riadky; ratame validne a nevalidne zaznamy
        for i, row in enumerate(reader, start=2):
            name = row.get("name", "")
            age = row.get("age", "")
            banner = row.get("banner_id", "")
            if (
                is_valid_name(name)
                and is_valid_age(age, settings.min_age, settings.max_age)
                and is_valid_banner_id(banner)
            ):
                valid += 1
            else:
                invalid += 1

    # Tlacime sumar v JSON forme (bez straty unicode znakov)
    click.echo(json.dumps({"valid": valid, "invalid": invalid}, ensure_ascii=False))


@main.command("send")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=str))
def send_cmd(csv_path: str):
    """Validacia a odoslanie v batchoch (aktualne stub; bez realnej siete).

    Kroky:
      1) nacitat CSV
      2) filtrovat len validne riadky
      3) rozdelit do batch-ov (<= BULK_BATCH_SIZE)
      4) odoslat cez ShowAdsClient.send_bulk (MVP stub)
      5) vytlacit sumar JSON {"sent": N, "note": "..."}
    """
    client = ShowAdsClient()
    rows = []

    # Nacitame a rovno filtrujeme validne polozky
    with open(csv_path, newline="", encoding="utf-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (
                is_valid_name(row.get("name", ""))
                and is_valid_age(row.get("age", ""), settings.min_age, settings.max_age)
                and is_valid_banner_id(row.get("banner_id", ""))
            ):
                rows.append(
                    {
                        "name": row["name"].strip(),
                        "age": int(row["age"]),
                        "banner_id": int(row["banner_id"]),
                    }
                )

    # Batching podla konfiguracie (default 1000)
    sent = 0
    for batch in chunked(rows, settings.bulk_batch_size):
        # Teraz stub; neskor realne POST na /banners/show/bulk + retry/backoff
        resp = client.send_bulk(batch)
        sent += len(batch)

    click.echo(
        json.dumps(
            {"sent": sent, "note": "network calls are stubbed in initial commit"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
