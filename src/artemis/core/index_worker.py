"""Indexing in the background, so the interactive path never waits for it.

The worker runs the vector index in its own thread. If the embedding model is
not running, it stops quietly and writes that to the audit log, and the answer
path falls back to matching file names.
"""

from __future__ import annotations

import threading

from artemis.core.embedder import EmbedError
from artemis.core.vector_index import VectorIndex
from artemis.data.store import Store


class IndexWorker:
    def __init__(self, store: Store, index: VectorIndex) -> None:
        self.store = store
        self.index = index
        self.thread: threading.Thread | None = None

    def start(self, workspace_id: int) -> None:
        if self.is_running():
            return
        self.thread = threading.Thread(
            target=self.run, args=(workspace_id,), daemon=True
        )
        self.thread.start()

    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def wait(self, timeout: float = 30.0) -> None:
        if self.thread is not None:
            self.thread.join(timeout)

    def run(self, workspace_id: int) -> None:
        try:
            embedded = self.index.index_workspace(workspace_id)
        except EmbedError as exc:
            self.store.append_audit(
                event="index.embed",
                outcome="unavailable",
                workspace_id=workspace_id,
                detail={"reason": str(exc)[:200]},
            )
            return
        self.store.append_audit(
            event="index.embed",
            outcome="completed",
            workspace_id=workspace_id,
            detail={"chunks_embedded": embedded},
        )