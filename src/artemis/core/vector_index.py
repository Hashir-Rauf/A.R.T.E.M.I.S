"""The vector index: search a workspace's files by meaning.

One sqlite file per workspace, inside that workspace's own index folder. Search
opens only the folder of the workspace you ask about, so one workspace cannot
read another's vectors. Revoking a workspace deletes its folder, and the index
goes with it.

Every file is read through the broker, so nothing outside the grant is embedded.
Indexing is incremental: a chunk whose text has not changed keeps its vector.

Search is fast because vectors are stored as raw bytes and kept in memory as one
numpy matrix per workspace. The matrix is loaded on the first search and loaded
again only when the index file changes.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import numpy as np

from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.chunking import chunk_text
from artemis.core.context import Chunk, Provenance
from artemis.core.embedder import Embedder
from artemis.core.errors import BoundaryRefusal
from artemis.data import paths
from artemis.data.store import Store

MAX_FILE_BYTES = 2 * 1024 * 1024
SCHEMA_VERSION = 2

TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path     TEXT    NOT NULL,
    line_start   INTEGER NOT NULL,
    line_end     INTEGER NOT NULL,
    content_hash TEXT    NOT NULL,
    text         TEXT    NOT NULL,
    vector       BLOB    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(rel_path);
"""


class VectorIndex:
    def __init__(self, store: Store, broker: WorkspaceBroker, embedder: Embedder) -> None:
        self.store = store
        self.broker = broker
        self.embedder = embedder
        self.cache: dict[int, tuple[tuple[int, int], np.ndarray, np.ndarray]] = {}
        self.lock = threading.Lock()

    def db_path(self, workspace_id: int) -> Path:
        return paths.index_dir(workspace_id) / "vectors.db"

    def connect(self, workspace_id: int) -> sqlite3.Connection:
        paths.index_dir(workspace_id).mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db_path(workspace_id))
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            # the index is derived data, so an older layout is simply rebuilt
            db.execute("DROP TABLE IF EXISTS chunks")
            db.executescript(TABLE)
            db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            db.commit()
        else:
            db.executescript(TABLE)
        return db

    def to_bytes(self, vector: list[float]) -> bytes:
        array = np.asarray(vector, dtype=np.float32)
        length = float(np.linalg.norm(array))
        if length > 0:
            array = array / length
        return array.astype(np.float32).tobytes()

    def read_text(self, workspace_id: int, rel_path: str) -> str | None:
        try:
            resolved = self.broker.resolve(workspace_id, rel_path, Operation.READ)
            path: Path = resolved.path
            if path.stat().st_size > MAX_FILE_BYTES:
                return None
            raw = path.read_bytes()
        except (BoundaryRefusal, OSError):
            return None
        if b"\x00" in raw:
            return None
        return raw.decode("utf-8", errors="replace")

    def index_file(self, workspace_id: int, rel_path: str) -> int:
        """Index one file. Returns how many chunks had to be embedded."""
        text = self.read_text(workspace_id, rel_path)
        db = self.connect(workspace_id)
        try:
            if text is None:
                db.execute("DELETE FROM chunks WHERE rel_path = ?", (rel_path,))
                db.commit()
                return 0

            old = {
                row[0]: row[1]
                for row in db.execute(
                    "SELECT content_hash, vector FROM chunks WHERE rel_path = ?",
                    (rel_path,),
                )
            }
            rows = []
            embedded = 0
            for chunk in chunk_text(text):
                vector = old.get(chunk.content_hash)
                if vector is None:
                    vector = self.to_bytes(self.embedder.embed(chunk.text))
                    embedded += 1
                rows.append(
                    (rel_path, chunk.line_start, chunk.line_end,
                     chunk.content_hash, chunk.text, vector)
                )

            db.execute("DELETE FROM chunks WHERE rel_path = ?", (rel_path,))
            db.executemany(
                "INSERT INTO chunks (rel_path, line_start, line_end, content_hash, text, vector)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            db.commit()
            return embedded
        finally:
            db.close()

    def remove_file(self, workspace_id: int, rel_path: str) -> None:
        db = self.connect(workspace_id)
        try:
            db.execute("DELETE FROM chunks WHERE rel_path = ?", (rel_path,))
            db.commit()
        finally:
            db.close()

    def index_workspace(self, workspace_id: int) -> int:
        """Index every file the file index lists. Returns chunks embedded."""
        listed = [row["rel_path"] for row in self.store.list_files(workspace_id)]
        total = 0
        for rel_path in listed:
            total += self.index_file(workspace_id, rel_path)

        db = self.connect(workspace_id)
        try:
            stored = [r[0] for r in db.execute("SELECT DISTINCT rel_path FROM chunks")]
        finally:
            db.close()
        for rel_path in stored:
            if rel_path not in listed:
                self.remove_file(workspace_id, rel_path)
        return total

    def load_matrix(self, workspace_id: int) -> tuple[np.ndarray, np.ndarray]:
        """The workspace's vectors as one matrix, kept until the index file changes."""
        db = self.connect(workspace_id)
        try:
            stat = self.db_path(workspace_id).stat()
            key = (stat.st_mtime_ns, stat.st_size)
            with self.lock:
                cached = self.cache.get(workspace_id)
                if cached is not None and cached[0] == key:
                    return cached[1], cached[2]
                rows = db.execute("SELECT id, vector FROM chunks").fetchall()
                if not rows:
                    ids = np.zeros(0, dtype=np.int64)
                    matrix = np.zeros((0, 0), dtype=np.float32)
                else:
                    size = len(rows[0][1])
                    good = [(i, v) for i, v in rows if len(v) == size]
                    ids = np.array([i for i, _ in good], dtype=np.int64)
                    joined = b"".join(v for _, v in good)
                    matrix = np.frombuffer(joined, dtype=np.float32).reshape(
                        len(good), size // 4
                    )
                self.cache[workspace_id] = (key, ids, matrix)
                return ids, matrix
        finally:
            db.close()

    def search(self, workspace_id: int, query: str, limit: int = 5) -> list[Chunk]:
        query_vector = np.asarray(self.embedder.embed(query), dtype=np.float32)
        length = float(np.linalg.norm(query_vector))
        if length == 0:
            return []
        query_vector = query_vector / length

        ids, matrix = self.load_matrix(workspace_id)
        if len(ids) == 0 or matrix.shape[1] != query_vector.shape[0]:
            return []

        scores = matrix @ query_vector
        count = min(limit, len(scores))
        if count < len(scores):
            top = np.argpartition(-scores, count - 1)[:count]
        else:
            top = np.arange(len(scores))
        top = top[np.argsort(-scores[top])]
        top = [int(i) for i in top if scores[i] > 0]
        if not top:
            return []

        wanted = [int(ids[i]) for i in top]
        db = self.connect(workspace_id)
        try:
            marks = ",".join("?" * len(wanted))
            found = {
                row[0]: row[1:]
                for row in db.execute(
                    "SELECT id, rel_path, line_start, line_end, text FROM chunks"
                    f" WHERE id IN ({marks})",
                    wanted,
                )
            }
        finally:
            db.close()

        results = []
        for position, chunk_id in zip(top, wanted):
            if chunk_id not in found:
                continue
            rel_path, line_start, line_end, text = found[chunk_id]
            results.append(
                Chunk(
                    text=text,
                    provenance=Provenance.WORKSPACE_FILE,
                    workspace_id=workspace_id,
                    source=rel_path,
                    line_start=line_start,
                    line_end=line_end,
                    score=float(scores[position]),
                )
            )
        return results