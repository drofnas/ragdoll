from __future__ import annotations

import signal
import threading
import time
from collections.abc import Callable, Mapping
from types import FrameType
from typing import Any

from ragdoll.core.config import get_settings
from ragdoll.core.logging import get_logger, setup_logging
from ragdoll.workers.document_pipeline import process_next_document_job

logger = get_logger("ragdoll.workers.document_worker")


def install_worker_signal_handlers(stop_event: threading.Event) -> dict[int, Any]:
    """Register SIGINT and SIGTERM handlers that stop the worker loop."""
    previous_handlers: dict[int, Any] = {}

    def _handle_shutdown(signum: int, _frame: FrameType | None) -> None:
        logger.info("Received shutdown signal signum=%s; stopping document worker.", signum)
        stop_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, _handle_shutdown)

    return previous_handlers


def restore_worker_signal_handlers(previous_handlers: Mapping[int, Any]) -> None:
    """Restore previous process signal handlers after the worker exits."""
    for signum, handler in previous_handlers.items():
        signal.signal(signum, handler)


def run_document_worker(
    *,
    stop_event: threading.Event | None = None,
    poll_interval_seconds: float | None = None,
    process_job: Callable[[], bool] = process_next_document_job,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Continuously claim and process document jobs until shutdown is requested."""
    settings = get_settings()
    setup_logging(settings)

    active_stop_event = stop_event or threading.Event()
    idle_poll_interval = (
        settings.document_worker_poll_interval_seconds
        if poll_interval_seconds is None
        else poll_interval_seconds
    )

    logger.info(
        "Starting document worker poll_interval_seconds=%s",
        idle_poll_interval,
    )

    while not active_stop_event.is_set():
        try:
            processed = process_job()
        except Exception:
            logger.exception("Document worker iteration failed; continuing after backoff.")
            processed = False

        if active_stop_event.is_set():
            break

        if not processed:
            sleep_fn(idle_poll_interval)

    logger.info("Document worker stopped.")


def main() -> None:
    stop_event = threading.Event()
    previous_handlers = install_worker_signal_handlers(stop_event)
    try:
        run_document_worker(stop_event=stop_event)
    finally:
        restore_worker_signal_handlers(previous_handlers)


if __name__ == "__main__":
    main()
