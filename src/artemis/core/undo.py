"""The Undo Journal.

Records how to reverse every change before that change is made, so a plan the
user approved can be taken back afterwards (Architecture Section 6.2).

Two decisions in here carry the weight.

**Snapshots happen before mutation, never after.** Recording the inverse after
the fact captures the state the operation already produced, which reverses to
nothing. Every path through this module writes the journal entry first and only
then lets the caller act.

**Undo works at plan granularity.** Reversing a folder tidy restores all twelve
moves together, in reverse order, because a plan is the unit the user was asked
about. Twelve separate undos would technically be equivalent and is not what was
approved. Per-operation undo exists but is secondary.

Strategy is chosen by cost: a small file is copied into the blob store, a large
one is hardlinked where the filesystem allows it, and a move or a new file needs
no content copy at all because the inverse is purely structural.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from artemis.data import paths
from artemis.data.store import Store

#: Above this, a snapshot is hardlinked rather than copied, when possible.
LARGE_FILE_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class JournalEntry:
    """One reversible step, with everything needed to undo it."""

    entry_id: int
    plan_id: str
    workspace_id: int
    forward: dict[str, Any]
    inverse: dict[str, Any]
    snapshot_ref: str | None
    created_at: str


class UndoJournal:
    """Records inverse operations, and replays them on request."""

    def __init__(self, store: Store) -> None:
        self._store = store

    # -- recording ---------------------------------------------------------

    def record_write(
        self, plan_id: str, workspace_id: int, target: Path
    ) -> JournalEntry:
        """Before writing to `target`, capture whatever is there now.

        If the file does not exist yet, the inverse is a deletion: undoing a
        file's creation means removing it. If it does exist, its current
        contents are snapshotted so they can be put back.
        """
        if target.exists():
            snapshot = self._snapshot(target)
            inverse = {"op": "restore", "path": str(target), "snapshot": snapshot}
        else:
            snapshot = None
            inverse = {"op": "remove_created", "path": str(target)}
        return self._append(
            plan_id,
            workspace_id,
            forward={"op": "write", "path": str(target)},
            inverse=inverse,
            snapshot_ref=snapshot,
        )

    def record_move(
        self, plan_id: str, workspace_id: int, source: Path, destination: Path
    ) -> JournalEntry:
        """A move needs no content copy: the inverse is the opposite move."""
        return self._append(
            plan_id,
            workspace_id,
            forward={"op": "move", "from": str(source), "to": str(destination)},
            inverse={"op": "move", "from": str(destination), "to": str(source)},
            snapshot_ref=None,
        )

    def record_mkdir(
        self, plan_id: str, workspace_id: int, target: Path
    ) -> JournalEntry:
        """Undoing a created directory removes it, but only if still empty.

        Refusing to remove a non-empty directory is deliberate: something the
        user put there afterwards must not disappear as a side effect of undo.
        """
        return self._append(
            plan_id,
            workspace_id,
            forward={"op": "mkdir", "path": str(target)},
            inverse={"op": "rmdir_if_empty", "path": str(target)},
            snapshot_ref=None,
        )

    # -- reversal ----------------------------------------------------------

    def entries_for_plan(self, plan_id: str) -> list[JournalEntry]:
        rows = self._store.query(
            "SELECT * FROM undo_journal WHERE plan_id = ? ORDER BY id", (plan_id,)
        )
        return [self._to_entry(row) for row in rows]

    def undo_plan(self, plan_id: str) -> tuple[int, list[str]]:
        """Reverse a whole plan, newest step first.

        Returns how many steps were reversed and any problems encountered.
        Reverse order matters: a plan that creates a folder and then moves files
        into it must move the files back before the folder can be removed.

        A step that cannot be reversed is reported rather than raised, so one
        awkward file does not abandon the remaining eleven.
        """
        entries = self.entries_for_plan(plan_id)
        if not entries:
            return 0, [f"nothing recorded for plan {plan_id}"]

        problems: list[str] = []
        reversed_count = 0
        for entry in reversed(entries):
            try:
                self._apply_inverse(entry.inverse)
                reversed_count += 1
            except OSError as exc:
                problems.append(f"{entry.inverse.get('op')}: {exc}")

        workspace_id = entries[0].workspace_id
        self._store.append_audit(
            event="undo.plan",
            outcome="reversed" if not problems else "partial",
            workspace_id=workspace_id,
            detail={
                "plan_id": plan_id,
                "steps": len(entries),
                "reversed": reversed_count,
                "problems": problems,
            },
        )
        if not problems:
            with self._store._write() as conn:  # noqa: SLF001 - store-owned table
                conn.execute("DELETE FROM undo_journal WHERE plan_id = ?", (plan_id,))
        return reversed_count, problems

    def _apply_inverse(self, inverse: dict[str, Any]) -> None:
        op = inverse.get("op")
        if op == "restore":
            blob = paths.blobs_dir() / str(inverse["snapshot"])
            target = Path(inverse["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(blob, target)
        elif op == "remove_created":
            Path(inverse["path"]).unlink(missing_ok=True)
        elif op == "move":
            source = Path(inverse["from"])
            destination = Path(inverse["to"])
            if source.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
        elif op == "rmdir_if_empty":
            target = Path(inverse["path"])
            if target.is_dir() and not any(target.iterdir()):
                target.rmdir()
        else:
            raise OSError(f"unknown inverse operation: {op}")

    # -- internals ---------------------------------------------------------

    def _snapshot(self, source: Path) -> str:
        """Copy a file into the blob store, addressed by its content hash.

        Content addressing means ten snapshots of a barely-changed file cost one
        copy, and an unchanged file costs nothing on the second snapshot.
        """
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        name = digest.hexdigest()
        blob = paths.blobs_dir() / name
        if blob.exists():
            return name

        size = source.stat().st_size
        if size > LARGE_FILE_BYTES:
            # A hardlink costs no space, but only within one filesystem, and
            # only while the original is not replaced in place. Copying is the
            # fallback rather than the failure.
            try:
                os.link(source, blob)
                return name
            except OSError:
                pass
        shutil.copy2(source, blob)
        return name

    def _append(
        self,
        plan_id: str,
        workspace_id: int,
        forward: dict[str, Any],
        inverse: dict[str, Any],
        snapshot_ref: str | None,
    ) -> JournalEntry:
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._store._write() as conn:  # noqa: SLF001 - store-owned table
            cursor = conn.execute(
                "INSERT INTO undo_journal"
                " (workspace_id, plan_id, forward_op, inverse_op, snapshot_ref, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    workspace_id,
                    plan_id,
                    json.dumps(forward, sort_keys=True),
                    json.dumps(inverse, sort_keys=True),
                    snapshot_ref,
                    created,
                ),
            )
        return JournalEntry(
            entry_id=int(cursor.lastrowid),
            plan_id=plan_id,
            workspace_id=workspace_id,
            forward=forward,
            inverse=inverse,
            snapshot_ref=snapshot_ref,
            created_at=created,
        )

    @staticmethod
    def _to_entry(row: Any) -> JournalEntry:
        return JournalEntry(
            entry_id=row["id"],
            plan_id=row["plan_id"],
            workspace_id=row["workspace_id"],
            forward=json.loads(row["forward_op"]),
            inverse=json.loads(row["inverse_op"]),
            snapshot_ref=row["snapshot_ref"],
            created_at=row["created_at"],
        )
