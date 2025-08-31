"""CLI rozhranie pre ShowAds konektor."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import sys
import time

import click

from .config import Settings, resolve_settings
from .csv_processor import CSVProcessor, REQUIRED_HEADERS, chunk, parse_csv
from .api_client import ShowAdsClient
from .sender import send_batches
from .logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@click.group(help="ShowAds CSV -> API konektor")
@click.option("--min-age", type=int, default=None)
@click.option("--max-age", type=int, default=None)
@click.option("--bulk-batch-size", type=int, default=None)
@click.option("--parallel-requests", type=int, default=None)
@click.option(
    "--dedup-window", type=int, default=None, help="velkost pametoveho okna pre deduplikaciu"
)
@click.pass_context  # type: ignore[arg-type]
def main(ctx: click.Context, **cli_opts: int | None) -> None:
    ctx.obj = resolve_settings(cli_opts)


@main.command("validate")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option(
    "--errors-out",
    type=click.Path(dir_okay=False, writable=True, path_type=str),
    default=None,
    help="CSV so zaznamami, ktore nepresli validaciou",
)
@click.pass_obj
def validate_cmd(settings: Settings, csv_path: str, errors_out: str | None) -> None:
    """Validacia CSV a sumarizacia vysledkov (bez siete)."""

    start = time.perf_counter()
    logger.info(
        "run_start", extra={"event": "run_start", "command": "validate", "csv_path": csv_path}
    )
    err_f = open(errors_out, "w", encoding="utf-8", newline="") if errors_out else None
    err_writer = csv.writer(err_f) if err_f else None
    if err_writer:
        err_writer.writerow(["name", "age", "banner_id", "cookie", "error"])
    try:
        processor = CSVProcessor(csv_path, settings.min_age, settings.max_age, err_writer)
    except ValueError as e:
        if err_f:
            err_f.close()
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(2)

    valid = sum(1 for _ in processor)
    invalid = processor.invalid_rows

    duration = round(time.perf_counter() - start, 3)
    if err_f:
        err_f.close()
    logger.info(
        "summary",
        extra={
            "event": "summary",
            "command": "validate",
            "valid": valid,
            "invalid": invalid,
            "duration_s": duration,
        },
    )
    click.echo(json.dumps({"valid": valid, "invalid": invalid}, ensure_ascii=False))


@main.command("send")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=str))
@click.option("--dry-run", is_flag=True, help="namiesto odoslania vypisat sumar")
@click.option(
    "--dry-run-output",
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help="CSV so vzorkou dat, ktore by sa poslali",
)
@click.option(
    "--dry-run-limit",
    type=int,
    default=10,
    show_default=True,
    help="Maximalny pocet riadkov vo vystupnom CSV pri dry-run",
)
@click.option(
    "--metrics-out",
    type=click.Path(dir_okay=False, writable=True, path_type=str),
    default=None,
    help="JSON subor s metrikami behu",
)
@click.option(
    "--errors-out",
    type=click.Path(dir_okay=False, writable=True, path_type=str),
    default=None,
    help="CSV so zaznamami, ktore nepresli validaciou",
)
@click.option("--no-progress", is_flag=True, help="Vypne ukazovateľ priebehu")
@click.pass_obj
def send_cmd(
    settings: Settings,
    csv_path: str,
    dry_run: bool,
    dry_run_output: str | None,
    dry_run_limit: int,
    metrics_out: str | None,
    errors_out: str | None,
    no_progress: bool,
) -> None:
    """Validacia a odoslanie v batchoch."""

    err_f = open(errors_out, "w", encoding="utf-8", newline="") if errors_out else None
    err_writer = csv.writer(err_f) if err_f else None
    if err_writer:
        err_writer.writerow(["name", "age", "banner_id", "cookie", "error"])
    try:
        rows_iter, stats = parse_csv(
            csv_path,
            settings.min_age,
            settings.max_age,
            dedup_window=settings.dedup_window,
            error_writer=err_writer,
        )
    except ValueError as e:
        if err_f:
            err_f.close()
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(2)

    logger.info(
        "run_start",
        extra={
            "event": "run_start",
            "command": "send",
            "csv_path": csv_path,
            "batch_size": settings.bulk_batch_size,
        },
    )

    if dry_run:
        sample: list[dict[str, int | str]] = []
        for row in rows_iter:
            if len(sample) < dry_run_limit:
                sample.append(row)
        summary = {
            "rows_read": stats.valid + stats.invalid,
            "rows_valid": stats.valid,
            "rows_invalid": stats.invalid,
            "rows_would_send": stats.unique,
        }
        click.echo(json.dumps(summary, ensure_ascii=False))
        if dry_run_output:
            with open(dry_run_output, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(REQUIRED_HEADERS))
                writer.writeheader()
                for entry in sample:
                    writer.writerow({k: str(v) for k, v in entry.items()})
        logger.info("summary", extra={"event": "summary", **summary})
        if err_f:
            err_f.close()
        return

    client = ShowAdsClient()
    auth_start = time.perf_counter()
    client.authenticate()
    auth_time = round(time.perf_counter() - auth_start, 3)

    batch_size = min(settings.bulk_batch_size, 1000)
    batches = chunk(rows_iter, batch_size)
    show_progress = not no_progress and sys.stderr.isatty()
    pbar = None
    if show_progress:
        from tqdm import tqdm  # type: ignore[import-untyped]

        pbar = tqdm(unit="rows")
    send_start = time.perf_counter()
    send_metrics = asyncio.run(
        send_batches(
            client,
            batches,
            settings.parallel_requests,
            settings.max_retries,
            settings.retry_backoff_s,
            pbar.update if pbar else None,
        )
    )
    send_time = round(time.perf_counter() - send_start, 3)
    if pbar:
        pbar.total = stats.unique
        pbar.close()

    avg_batch_time = (
        round(send_metrics.total_batch_time_s / send_metrics.total_batches, 3)
        if send_metrics.total_batches
        else 0
    )
    metrics: dict[str, float | int] = {
        "rows_read": stats.valid + stats.invalid,
        "rows_valid": stats.valid,
        "rows_invalid": stats.invalid,
        "auth_time_s": auth_time,
        "send_time_s": send_time,
        "rows_sent": send_metrics.sent,
        "rows_failed": send_metrics.failed,
        "rate_limited": send_metrics.rate_limited,
        "final_parallel": send_metrics.final_parallel,
        "final_backoff": send_metrics.final_backoff,
        "total_batches": send_metrics.total_batches,
        "total_retries": send_metrics.total_retries,
        "max_retries": send_metrics.max_retries,
        "avg_batch_time_s": avg_batch_time,
    }

    output_metrics = {"sent": send_metrics.sent, **metrics}
    if metrics_out:
        with open(metrics_out, "w", encoding="utf-8") as mf:
            json.dump(output_metrics, mf, ensure_ascii=False)

    if err_f:
        err_f.close()

    logger.info("summary", extra={"event": "summary", **metrics})
    click.echo(json.dumps(output_metrics, ensure_ascii=False))
    if send_metrics.sent == 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
