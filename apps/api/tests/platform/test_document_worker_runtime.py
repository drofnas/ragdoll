from __future__ import annotations

import signal
import threading

from ragdoll.workers import document_worker


def test_document_worker_processes_queued_jobs_and_stops():
    stop_event = threading.Event()
    process_calls: list[str] = []
    sleep_calls: list[float] = []

    def fake_process_job() -> bool:
        process_calls.append("processed")
        stop_event.set()
        return True

    document_worker.run_document_worker(
        stop_event=stop_event,
        poll_interval_seconds=0.25,
        process_job=fake_process_job,
        sleep_fn=sleep_calls.append,
    )

    assert process_calls == ["processed"]
    assert sleep_calls == []


def test_document_worker_sleeps_when_queue_is_empty():
    stop_event = threading.Event()
    sleep_calls: list[float] = []
    process_calls: list[str] = []

    def fake_process_job() -> bool:
        process_calls.append("empty")
        return False

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        stop_event.set()

    document_worker.run_document_worker(
        stop_event=stop_event,
        poll_interval_seconds=0.5,
        process_job=fake_process_job,
        sleep_fn=fake_sleep,
    )

    assert process_calls == ["empty"]
    assert sleep_calls == [0.5]


def test_install_worker_signal_handlers_sets_stop_event(monkeypatch):
    stop_event = threading.Event()
    registered_handlers: dict[int, object] = {}

    monkeypatch.setattr(document_worker.signal, "getsignal", lambda signum: f"previous-{signum}")

    def fake_signal(signum: int, handler: object) -> None:
        registered_handlers[signum] = handler

    monkeypatch.setattr(document_worker.signal, "signal", fake_signal)

    previous_handlers = document_worker.install_worker_signal_handlers(stop_event)

    assert previous_handlers[signal.SIGINT] == f"previous-{signal.SIGINT}"
    assert previous_handlers[signal.SIGTERM] == f"previous-{signal.SIGTERM}"

    sigterm_handler = registered_handlers[signal.SIGTERM]
    assert callable(sigterm_handler)
    sigterm_handler(signal.SIGTERM, None)
    assert stop_event.is_set()


def test_document_worker_continues_after_iteration_failure():
    stop_event = threading.Event()
    sleep_calls: list[float] = []
    attempts = 0

    def fake_process_job() -> bool:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("queue temporarily unavailable")
        stop_event.set()
        return True

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    document_worker.run_document_worker(
        stop_event=stop_event,
        poll_interval_seconds=0.2,
        process_job=fake_process_job,
        sleep_fn=fake_sleep,
    )

    assert attempts == 2
    assert sleep_calls == [0.2]
