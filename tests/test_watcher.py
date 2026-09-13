"""The file watcher, exercised through its real timer thread.

These tests exist because the first version of the watcher was completely broken
while the rest of the suite passed. `Indexer.scan` and `Indexer.touch` were
covered directly, on the main thread, so nothing ever ran the debounce timer.
The timer fires on its own thread, and the SQLite connection had been opened on
the main one, so every flush raised ProgrammingError inside that thread and the
index silently never changed.

The lesson generalises: testing a component's methods is not the same as testing
the path production actually takes to reach them. Anything that crosses a thread
boundary needs a test that crosses it too.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from artemis.core.broker import WorkspaceBroker
from artemis.core.indexer import Indexer, WorkspaceWatcher
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store

# Short, so the tests stay fast; the production default is two seconds.
DEBOUNCE = 0.15


def _settle(watcher: WorkspaceWatcher, seconds: float = 0.6) -> None:
    """Give the observer time to deliver events, then force a flush."""
    time.sleep(seconds)
    watcher.flush_now()
    time.sleep(0.2)


def test_watcher_indexes_a_new_file(
    manager: WorkspaceManager, indexer: Indexer, broker: WorkspaceBroker,
    store: Store, sandbox: Path,
) -> None:
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    watcher = WorkspaceWatcher(store, broker, indexer, debounce=DEBOUNCE)
    watcher.start(ws.id)
    try:
        (sandbox / "added.txt").write_text("new", encoding="utf-8")
        _settle(watcher)
        indexed = {r["rel_path"] for r in store.list_files(ws.id)}
    finally:
        watcher.stop()
    assert "added.txt" in indexed


def test_watcher_drops_a_deleted_file(
    manager: WorkspaceManager, indexer: Indexer, broker: WorkspaceBroker,
    store: Store, sandbox: Path,
) -> None:
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    watcher = WorkspaceWatcher(store, broker, indexer, debounce=DEBOUNCE)
    watcher.start(ws.id)
    try:
        (sandbox / "readme.txt").unlink()
        _settle(watcher)
        indexed = {r["rel_path"] for r in store.list_files(ws.id)}
    finally:
        watcher.stop()
    assert "readme.txt" not in indexed


def test_watcher_survives_a_burst_of_writes(
    manager: WorkspaceManager, indexer: Indexer, broker: WorkspaceBroker,
    store: Store, sandbox: Path,
) -> None:
    """A burst must coalesce and must not raise on the timer thread."""
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    watcher = WorkspaceWatcher(store, broker, indexer, debounce=DEBOUNCE)
    watcher.start(ws.id)
    try:
        target = sandbox / "busy.txt"
        for i in range(12):
            target.write_text(f"revision {i}", encoding="utf-8")
        _settle(watcher)
        indexed = {r["rel_path"] for r in store.list_files(ws.id)}
    finally:
        watcher.stop()
    assert "busy.txt" in indexed
    assert store.verify_audit_chain()


def test_store_is_usable_from_another_thread(store: Store, sandbox: Path) -> None:
    """The defect in isolation: the store must serve a non-creating thread."""
    manager = WorkspaceManager(store)
    ws = manager.grant(sandbox)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            store.upsert_file(ws.id, "from-thread.txt", 1.0, 3)
            store.append_audit("test.thread", "ok", ws.id)
            store.list_files(ws.id)
        except BaseException as exc:  # noqa: BLE001 - recorded and re-raised below
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)

    assert not errors, f"store raised across a thread boundary: {errors[0]!r}"
    assert any(
        r["rel_path"] == "from-thread.txt" for r in store.list_files(ws.id)
    )


def test_concurrent_audit_writes_keep_the_chain_intact(
    store: Store, sandbox: Path
) -> None:
    """Parallel appends must not fork the hash chain.

    Each entry chains onto the previous one, so read-then-append has to be
    atomic; otherwise two threads chain onto the same predecessor.
    """
    ws = WorkspaceManager(store).grant(sandbox).id
    barrier = threading.Barrier(4)

    def worker(n: int) -> None:
        barrier.wait()
        for i in range(5):
            store.append_audit("test.concurrent", "ok", ws, {"w": n, "i": i})

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert store.verify_audit_chain()
    assert store.count_audit() >= 20
