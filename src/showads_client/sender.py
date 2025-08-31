"""Nástroje pre paralelné odosielanie dávok s adaptívnym obmedzovaním rýchlosti."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

from .api_client import RateLimitError, ShowAdsClient

logger = logging.getLogger(__name__)


@dataclass
class SendMetrics:
    total: int = 0
    sent: int = 0
    failed: int = 0
    rate_limited: int = 0
    final_parallel: int = 0
    final_backoff: float = 0.0
    total_batches: int = 0
    total_retries: int = 0
    max_retries: int = 0
    total_batch_time_s: float = 0.0


async def _call_send(client: ShowAdsClient, payload: list[dict[str, Any]]) -> Any:
    return await asyncio.to_thread(client.send_bulk, payload)


async def send_batches(
    client: ShowAdsClient,
    batches: Iterable[list[dict[str, Any]]],
    parallel: int,
    max_retries: int,
    backoff_s: float,
    progress_cb: Callable[[int], None] | None = None,
) -> SendMetrics:
    """Odosiela dávky s obmedzenou paralelnosťou a adaptívnym obmedzením rýchlosti.

    Ak požiadavka skončí chybou ``RateLimitError``, zníži sa paralelnosť a
    zvýši sa odstup pred opakovaním neúspešnej dávky.
    """

    metrics = SendMetrics()
    queue: asyncio.Queue[tuple[int, list[dict[str, Any]]]] = asyncio.Queue(maxsize=parallel * 2)

    current_parallel = max(1, parallel)
    workers: list[asyncio.Task[Any]] = []

    async def adjust_workers() -> None:
        while len(workers) > current_parallel:
            task = workers.pop()
            task.cancel()
            with contextlib.suppress(Exception):
                await task

    async def worker() -> None:
        nonlocal current_parallel, backoff_s
        while True:
            idx, batch = await queue.get()
            tries = 0
            start = time.perf_counter()
            while True:
                try:
                    await _call_send(client, batch)
                    duration = time.perf_counter() - start
                    metrics.sent += len(batch)
                    metrics.total_batch_time_s += duration
                    metrics.total_retries += tries
                    metrics.max_retries = max(metrics.max_retries, tries)
                    logger.info(
                        "batch_sent",
                        extra={
                            "event": "batch_sent",
                            "batch_index": idx,
                            "size": len(batch),
                            "duration_s": round(duration, 3),
                            "retries": tries,
                        },
                    )
                    break
                except RateLimitError:
                    metrics.rate_limited += 1
                    tries += 1
                    if tries > max_retries:
                        duration = time.perf_counter() - start
                        metrics.failed += len(batch)
                        metrics.total_batch_time_s += duration
                        metrics.total_retries += tries
                        metrics.max_retries = max(metrics.max_retries, tries)
                        logger.error(
                            "batch_failed",
                            extra={
                                "event": "batch_failed",
                                "batch_index": idx,
                                "size": len(batch),
                                "duration_s": round(duration, 3),
                                "retries": tries,
                            },
                        )
                        break
                    current_parallel = max(1, current_parallel - 1)
                    backoff_s *= 2
                    await asyncio.sleep(backoff_s)
                    continue
            if progress_cb:
                progress_cb(len(batch))
            queue.task_done()
            await adjust_workers()

    async def producer() -> None:
        for idx, batch in enumerate(batches, start=1):
            metrics.total += len(batch)
            metrics.total_batches += 1
            await queue.put((idx, batch))

    for _ in range(current_parallel):
        workers.append(asyncio.create_task(worker()))

    prod_task = asyncio.create_task(producer())
    await prod_task
    await queue.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)

    metrics.final_parallel = current_parallel
    metrics.final_backoff = backoff_s
    return metrics
