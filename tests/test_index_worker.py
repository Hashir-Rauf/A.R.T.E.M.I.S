"""Background indexing: it must not block, and it must fail quietly."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.embedder import FakeEmbedder, OllamaEmbedder
from artemis.core.index_worker import IndexWorker
from artemis.core.indexer import Indexer
from artemis.core.vector_index import VectorIndex
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


class SlowEmbedder(FakeEmbedder):
    def embed(self, text: str) -> list[float]:
        time.sleep(0.2)
        return super().embed(text)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path, indexer: Indexer) -> int:
    workspace = manager.grant(sandbox)
    indexer.scan(workspace.id)
    return workspace.id


def test_start_returns_before_the_work_is_done(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    worker = IndexWorker(store, VectorIndex(store, broker, SlowEmbedder()))
    started = time.time()
    worker.start(workspace_id)
    assert time.time() - started < 0.15
    assert worker.is_running()
    worker.wait()
    assert not worker.is_running()


def test_a_finished_run_is_written_to_the_audit_log(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    worker = IndexWorker(store, VectorIndex(store, broker, FakeEmbedder()))
    worker.start(workspace_id)
    worker.wait()
    events = [(r["event"], r["outcome"]) for r in store.list_audit()]
    assert ("index.embed", "completed") in events


def test_a_missing_model_stops_quietly_and_is_logged(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    down = OllamaEmbedder(host="http://127.0.0.1:9", timeout_s=1)
    worker = IndexWorker(store, VectorIndex(store, broker, down))
    worker.start(workspace_id)
    worker.wait()
    events = [(r["event"], r["outcome"]) for r in store.list_audit()]
    assert ("index.embed", "unavailable") in events