"""The file index: what exists, and where.

This is the mechanical half of the memory design (Architecture Section 7.2). It
records paths, sizes, modification times and content hashes. It holds no
interpretation of file contents, and it is rebuildable at any time from the
filesystem, which is exactly what distinguishes it from memory proper.

Two behaviours matter for Sprint 2:

* Everything it indexes passes through the Workspace Broker first, so the index
  can only ever contain paths inside a grant.
* Watching is debounced. The architecture puts index updates at background
  priority (Section 10.1), so a burst of writes coalesces into one update per
  file rather than blocking on every event.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from artemis.core.broker import WorkspaceBroker
from artemis.data.store import Store

# Files larger than this are indexed by metadata only. Hashing a large file on
# every save would put disk cost on the interactive path for no benefit here.
MAX_HASH_BYTES = 8 * 1024 * 1024

DEBOUNCE_SECONDS = 2.0


def content_hash(path: Path, max_bytes: int = MAX_HASH_BYTES) -> str | None:
    """SHA-256 of a file's contents, or None if it is too large or unreadable."""
    try:
        if path.stat().st_size > max_bytes:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


class Indexer:
    """Builds and maintains the file index for granted workspaces."""

    def __init__(self, store: Store, broker: WorkspaceBroker) -> None:
        self._store = store
        self._broker = broker

    def scan(self, workspace_id: int) -> int:
        """Walk a workspace and index everything the broker admits.

        Returns the number of files indexed. Paths the broker refuses, such as a
        `.ssh` directory inside the granted folder, are skipped silently: they are
        not errors, they are simply outside what the grant covers.
        """
        row = self._store.get_workspace(workspace_id)
        if row is None:
            return 0
        root = Path(row["root"])
        seen: set[str] = set()
        count = 0

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if not self._broker.is_within_grant(workspace_id, path):
                continue
            rel = path.relative_to(root).as_posix()
            if self._record(workspace_id, path, rel):
                seen.add(rel)
                count += 1

        # Drop rows for files that have gone away since the last scan.
        for existing in self._store.list_files(workspace_id):
            if existing["rel_path"] not in seen:
                self._store.remove_file(workspace_id, existing["rel_path"])

        self._store.append_audit(
            event="index.scan",
            outcome="completed",
            workspace_id=workspace_id,
            detail={"files": count},
        )
        return count

    def _record(self, workspace_id: int, path: Path, rel: str) -> bool:
        try:
            stat = path.stat()
        except OSError:
            return False
        self._store.upsert_file(
            workspace_id=workspace_id,
            rel_path=rel,
            mtime=stat.st_mtime,
            size=stat.st_size,
            content_hash=content_hash(path),
            file_type=path.suffix.lstrip(".").lower() or None,
        )
        return True

    def forget(self, workspace_id: int, absolute: Path) -> None:
        """Remove one file's row, if it is inside the grant."""
        row = self._store.get_workspace(workspace_id)
        if row is None:
            return
        root = Path(row["root"])
        try:
            rel = absolute.resolve(strict=False).relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            return
        self._store.remove_file(workspace_id, rel)

    def touch(self, workspace_id: int, absolute: Path) -> None:
        """Re-index one file after a change, if the broker admits it."""
        if not self._broker.is_within_grant(workspace_id, absolute):
            return
        row = self._store.get_workspace(workspace_id)
        if row is None:
            return
        root = Path(row["root"])
        if not absolute.is_file():
            self.forget(workspace_id, absolute)
            return
        try:
            rel = absolute.relative_to(root).as_posix()
        except ValueError:
            return
        self._record(workspace_id, absolute, rel)


class _DebouncedHandler(FileSystemEventHandler):
    """Collects filesystem events and flushes them on a timer.

    Editors write a file several times in quick succession. Without debouncing
    that produces several index updates for one logical save.
    """

    def __init__(self, on_flush: Callable[[set[Path]], None], delay: float) -> None:
        self._on_flush = on_flush
        self._delay = delay
        self._pending: set[Path] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        with self._lock:
            self._pending.add(Path(str(event.src_path)))
            dest = getattr(event, "dest_path", None)
            if dest:
                self._pending.add(Path(str(dest)))
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            batch, self._pending = self._pending, set()
            self._timer = None
        if batch:
            self._on_flush(batch)

    def flush_now(self) -> None:
        """Force a flush without waiting for the timer. Used by tests."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._flush()


class WorkspaceWatcher:
    """Watches a granted workspace and keeps its file index current."""

    def __init__(
        self,
        store: Store,
        broker: WorkspaceBroker,
        indexer: Indexer,
        debounce: float = DEBOUNCE_SECONDS,
    ) -> None:
        self._store = store
        self._broker = broker
        self._indexer = indexer
        self._debounce = debounce
        self._observer: Observer | None = None  # type: ignore[valid-type]
        self._handler: _DebouncedHandler | None = None

    def start(self, workspace_id: int) -> None:
        row = self._store.get_workspace(workspace_id)
        if row is None:
            return
        root = Path(row["root"])

        def flush(paths: set[Path]) -> None:
            for path in paths:
                self._indexer.touch(workspace_id, path)

        self._handler = _DebouncedHandler(flush, self._debounce)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(root), recursive=True)
        self._observer.start()
        self._store.append_audit(
            event="watcher.start",
            outcome="started",
            workspace_id=workspace_id,
            detail={"root": str(root)},
        )

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._handler = None

    def flush_now(self) -> None:
        if self._handler is not None:
            self._handler.flush_now()
