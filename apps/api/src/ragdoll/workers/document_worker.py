"""Compatibility wrapper for the renamed document-vector worker."""

from ragdoll.workers.document_vector_worker import (
    install_worker_signal_handlers,
    main,
    restore_worker_signal_handlers,
    run_document_worker,
    signal,
)

__all__ = [
    "install_worker_signal_handlers",
    "main",
    "restore_worker_signal_handlers",
    "run_document_worker",
    "signal",
]
