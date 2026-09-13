"""The SQLite system of record.

Schema follows Architecture Section 7.1. Sprint 2 creates the whole table set but
only populates `workspaces`, `file_index` and `audit_log`; the remaining tables are
created now so that later sprints add behaviour rather than migrations.

Two design points worth stating, because both are load-bearing for the trust claim:

* Deleting a workspace cascades. Its file rows, sessions, memory, rules and index
  directory all go with it (Architecture Section 7.3). Foreign keys are declared
  ON DELETE CASCADE and enforced with `PRAGMA foreign_keys`, which SQLite leaves
  off by default and must be re-enabled on every connection.
* The audit log is append-only and hash-chained. Each row carries the hash of the
  previous row, so removing or editing an entry breaks the chain detectably. Sprint 2
  writes refusals into it; Sprint 3 adds approvals and actions.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from artemis.data import paths

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Grants. One row per folder the user has explicitly opted in.
CREATE TABLE IF NOT EXISTS workspaces (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    root         TEXT    NOT NULL UNIQUE,   -- canonical absolute path
    permission   TEXT    NOT NULL DEFAULT 'read_write',
    cloud_policy TEXT    NOT NULL DEFAULT 'local_only',
    created_at   TEXT    NOT NULL
);

-- What exists and where. Mechanical, rebuildable, holds no interpretation.
CREATE TABLE IF NOT EXISTS file_index (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    rel_path     TEXT    NOT NULL,
    mtime        REAL    NOT NULL,
    size         INTEGER NOT NULL,
    content_hash TEXT,
    file_type    TEXT,
    indexed_at   TEXT    NOT NULL,
    UNIQUE (workspace_id, rel_path)
);
CREATE INDEX IF NOT EXISTS idx_file_workspace ON file_index(workspace_id);

-- Append-only, hash-chained. Records refusals as well as actions.
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT    NOT NULL,
    workspace_id INTEGER,
    event        TEXT    NOT NULL,
    outcome      TEXT    NOT NULL,
    detail       TEXT    NOT NULL DEFAULT '{}',
    prev_hash    TEXT    NOT NULL,
    entry_hash   TEXT    NOT NULL
);

-- Created now, populated by later sprints.
CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    started_at   TEXT    NOT NULL,
    ended_at     TEXT,
    resume_state TEXT    NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS turns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ts         TEXT    NOT NULL,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_kv (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE,
    key          TEXT    NOT NULL,
    value        TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    UNIQUE (workspace_id, key)
);

CREATE TABLE IF NOT EXISTS automation_rules (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    description  TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'proposed',
    created_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS policy_rules (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    operation    TEXT    NOT NULL,
    decision     TEXT    NOT NULL,
    created_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS undo_journal (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    plan_id      TEXT    NOT NULL,
    forward_op   TEXT    NOT NULL,
    inverse_op   TEXT    NOT NULL,
    snapshot_ref TEXT,
    created_at   TEXT    NOT NULL
);
"""

GENESIS_HASH = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    """A connection to the local system of record.

    Usable as a context manager. Foreign keys are enabled per connection, which
    SQLite requires: without it the ON DELETE CASCADE clauses are silently inert
    and revoking a workspace would leave its rows behind.

    Thread safety. The file watcher flushes its debounce buffer on a timer
    thread, so the store is reached from more than one thread even though the
    interactive path is single-threaded. SQLite's own guard would reject that,
    so the connection is opened with `check_same_thread=False` and every
    statement is serialised behind `self._lock` instead. Disabling the guard
    without the lock would trade a loud error for silent corruption, so the two
    belong together. All access goes through `query`, `query_one` or `_write`;
    nothing outside this class touches the connection directly.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or paths.database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    # -- lifecycle ---------------------------------------------------------

    def _migrate(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)
            self._conn.execute(
                "INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._conn:
            yield self._conn

    # -- guarded reads -----------------------------------------------------

    def query(self, sql: str, args: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Run a read and return every row, holding the lock for the fetch."""
        with self._lock:
            return list(self._conn.execute(sql, args).fetchall())

    def query_one(self, sql: str, args: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Run a read and return the first row, or None."""
        with self._lock:
            return self._conn.execute(sql, args).fetchone()

    # -- workspaces --------------------------------------------------------

    def create_workspace(
        self,
        name: str,
        root: Path,
        permission: str = "read_write",
        cloud_policy: str = "local_only",
    ) -> int:
        """Record a grant. `root` must already be canonical and must exist."""
        with self._write() as conn:
            cur = conn.execute(
                "INSERT INTO workspaces (name, root, permission, cloud_policy, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (name, str(root), permission, cloud_policy, _now()),
            )
        workspace_id = int(cur.lastrowid)
        paths.index_dir(workspace_id).mkdir(parents=True, exist_ok=True)
        self.append_audit(
            event="workspace.grant",
            outcome="granted",
            workspace_id=workspace_id,
            detail={"name": name, "root": str(root), "permission": permission},
        )
        return workspace_id

    def get_workspace(self, workspace_id: int) -> sqlite3.Row | None:
        return self.query_one(
            "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
        )

    def list_workspaces(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM workspaces ORDER BY id")

    def delete_workspace(self, workspace_id: int) -> None:
        """Revoke a grant and everything derived from it.

        The row deletion cascades to file rows, sessions, memory, rules and the
        undo journal. The index directory is removed separately because the
        filesystem is not part of the transaction.
        """
        row = self.get_workspace(workspace_id)
        if row is None:
            return
        with self._write() as conn:
            conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
        shutil.rmtree(paths.index_dir(workspace_id), ignore_errors=True)
        self.append_audit(
            event="workspace.revoke",
            outcome="revoked",
            workspace_id=None,
            detail={"name": row["name"], "root": row["root"]},
        )

    # -- file index --------------------------------------------------------

    def upsert_file(
        self,
        workspace_id: int,
        rel_path: str,
        mtime: float,
        size: int,
        content_hash: str | None = None,
        file_type: str | None = None,
    ) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO file_index"
                " (workspace_id, rel_path, mtime, size, content_hash, file_type, indexed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (workspace_id, rel_path) DO UPDATE SET"
                "   mtime = excluded.mtime,"
                "   size = excluded.size,"
                "   content_hash = excluded.content_hash,"
                "   file_type = excluded.file_type,"
                "   indexed_at = excluded.indexed_at",
                (
                    workspace_id,
                    rel_path,
                    mtime,
                    size,
                    content_hash,
                    file_type,
                    _now(),
                ),
            )

    def remove_file(self, workspace_id: int, rel_path: str) -> None:
        with self._write() as conn:
            conn.execute(
                "DELETE FROM file_index WHERE workspace_id = ? AND rel_path = ?",
                (workspace_id, rel_path),
            )

    def list_files(self, workspace_id: int | None = None) -> list[sqlite3.Row]:
        if workspace_id is None:
            return self.query("SELECT * FROM file_index ORDER BY workspace_id, rel_path")
        return self.query(
            "SELECT * FROM file_index WHERE workspace_id = ? ORDER BY rel_path",
            (workspace_id,),
        )

    def count_files(self, workspace_id: int) -> int:
        row = self.query_one(
            "SELECT COUNT(*) AS n FROM file_index WHERE workspace_id = ?",
            (workspace_id,),
        )
        return int(row["n"]) if row else 0

    # -- audit log ---------------------------------------------------------

    def append_audit(
        self,
        event: str,
        outcome: str,
        workspace_id: int | None = None,
        detail: dict[str, Any] | None = None,
    ) -> str:
        """Append one hash-chained entry. Returns the new entry's hash.

        Refusals are recorded here as well as actions, so the log answers what was
        proposed, not only what happened.
        """
        payload = json.dumps(detail or {}, sort_keys=True, separators=(",", ":"))
        ts = _now()
        # Read the previous hash and append under one lock, so two threads
        # cannot both chain onto the same predecessor and fork the chain.
        with self._lock:
            prev = self._conn.execute(
                "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev["entry_hash"] if prev else GENESIS_HASH
            entry_hash = hashlib.sha256(
                "|".join(
                    [prev_hash, ts, str(workspace_id), event, outcome, payload]
                ).encode()
            ).hexdigest()
            with self._conn:
                self._conn.execute(
                    "INSERT INTO audit_log"
                    " (ts, workspace_id, event, outcome, detail, prev_hash, entry_hash)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ts, workspace_id, event, outcome, payload, prev_hash, entry_hash),
                )
        return entry_hash

    def list_audit(self, limit: int = 100) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        )

    def count_audit(self) -> int:
        row = self.query_one("SELECT COUNT(*) AS n FROM audit_log")
        return int(row["n"]) if row else 0

    def verify_audit_chain(self) -> bool:
        """Recompute the chain. False means an entry was altered or removed."""
        prev_hash = GENESIS_HASH
        for row in self.query("SELECT * FROM audit_log ORDER BY id"):
            expected = hashlib.sha256(
                "|".join(
                    [
                        prev_hash,
                        row["ts"],
                        str(row["workspace_id"]),
                        row["event"],
                        row["outcome"],
                        row["detail"],
                    ]
                ).encode()
            ).hexdigest()
            if expected != row["entry_hash"] or row["prev_hash"] != prev_hash:
                return False
            prev_hash = row["entry_hash"]
        return True
