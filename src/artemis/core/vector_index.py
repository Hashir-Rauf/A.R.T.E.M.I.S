"""The vector index: search a workspace's files by meaning.

One sqlite file per workspace, inside that workspace's own index folder. Search
opens only the folder of the workspace you ask about, so one workspace cannot
read another's vectors. Revoking a workspace deletes its folder, and the index
goes with it.

Every file is read through the broker, so nothing outside the grant is embedded.
Indexing is incremental: a chunk whose text has not changed keeps its vector.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.chunking import chunk_text
from artemis.core.context import Chunk, Provenance
from artemis.core.embedder import Embedder, cosine
from artemis.core.errors import BoundaryRefusal
from artemis.data import paths
from artemis.data.store import Store

MAX_FILE_BYTES = 2 * 1024 * 1024

TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path     TEXT    NOT NULL,
    line_start   INTEGER NOT NULL,
    line_end     INTEGER NOT NULL,
    content_hash TEXT    NOT NULL,
    text         TEXT    NOT NULL,
    vector       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(rel_path);
"""


class VectorIndex:
    def __init__(self, store: Store, broker: WorkspaceBroker, embedder: Embedder) -> None:
        self.store = store
        self.broker = broker
        self.embedder = embedder

    def connect(self, workspace_id: int) -> sqlite3.Connection:
        folder = paths.index_dir(workspace_id)
        folder.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(folder / "vectors.db")
        db.executescript(TABLE)
        return db

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
                    vector = json.dumps(self.embedder.embed(chunk.text))
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

    def search(self, workspace_id: int, query: str, limit: int = 5) -> list[Chunk]:
        query_vector = self.embedder.embed(query)
        db = self.connect(workspace_id)
        try:
            rows = db.execute(
                "SELECT rel_path, line_start, line_end, text, vector FROM chunks"
            ).fetchall()
        finally:
            db.close()

        scored = []
        for rel_path, line_start, line_end, text, vector in rows:
            score = cosine(query_vector, json.loads(vector))
            if score <= 0:
                continue
            scored.append(
                Chunk(
                    text=text,
                    provenance=Provenance.WORKSPACE_FILE,
                    workspace_id=workspace_id,
                    source=rel_path,
                    line_start=line_start,
                    line_end=line_end,
                    score=score,
                )
            )
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:limit]