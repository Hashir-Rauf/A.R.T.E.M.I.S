"""F1: Pick up where you left off.

Shows what changed in a workspace since it was last open, which files were
being worked on, and what the user said they were about to do next.

**No model is involved.** This is a deterministic replay of recorded state, and
that is a deliberate design choice rather than a simplification: the feature is
most valuable precisely when the user cannot remember what they were doing, and
a plausible-sounding reconstruction would be worse than useless at that moment.
Everything reported here is a fact read from the store or the filesystem.

Risk tier T0 throughout. The service reads; it changes nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.errors import BoundaryRefusal
from artemis.data.store import Store

#: How many changed files to report before summarising the rest.
MAX_LISTED = 12


@dataclass(frozen=True)
class ChangedFile:
    """A file that moved, appeared or vanished since the last session."""

    rel_path: str
    change: str  # "added" | "modified" | "removed"
    size: int = 0

    def describe(self) -> str:
        return f"{self.change}: {self.rel_path}"


@dataclass
class ResumeReport:
    """What the user is shown when they come back to a workspace."""

    workspace_id: int
    workspace_name: str
    last_seen: str | None
    note: str = ""
    recent_files: tuple[str, ...] = ()
    changes: tuple[ChangedFile, ...] = ()
    open_proposals: tuple[str, ...] = ()
    undoable_plans: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_first_visit(self) -> bool:
        return self.last_seen is None

    def summary(self) -> str:
        """One line in plain words, for the top of the panel."""
        if self.is_first_visit:
            return "This is the first time ARTEMIS has opened this folder."
        if not self.changes and not self.note:
            return f"Nothing has changed since {self.last_seen}."
        parts: list[str] = []
        if self.changes:
            added = sum(1 for c in self.changes if c.change == "added")
            modified = sum(1 for c in self.changes if c.change == "modified")
            removed = sum(1 for c in self.changes if c.change == "removed")
            bits = [
                f"{n} {label}"
                for n, label in ((added, "new"), (modified, "changed"), (removed, "gone"))
                if n
            ]
            parts.append(", ".join(bits) + f" since {self.last_seen}")
        if self.note:
            parts.append(f'you noted: "{self.note}"')
        return ". ".join(p[0].upper() + p[1:] for p in parts) + "."


class ResumeService:
    """Reconstructs what was happening when a workspace was last closed."""

    def __init__(self, store: Store, broker: WorkspaceBroker) -> None:
        self._store = store
        self._broker = broker

    # -- recording ---------------------------------------------------------

    def open_session(self, workspace_id: int) -> int:
        """Start a session and snapshot the workspace as it is now."""
        session_id = self._store.start_session(workspace_id)
        self._store.append_audit(
            event="resume.session",
            outcome="opened",
            workspace_id=workspace_id,
            detail={"session_id": session_id},
        )
        return session_id

    def close_session(
        self,
        session_id: int,
        workspace_id: int,
        note: str = "",
        recent_files: list[str] | None = None,
    ) -> None:
        """Record what to restore next time.

        The note is whatever the user said they were about to do. It is stored
        verbatim and replayed verbatim; ARTEMIS never paraphrases it, because a
        paraphrase of a half-finished thought is exactly the kind of thing that
        turns out to be wrong when it matters.
        """
        state = json.dumps(
            {
                "note": note,
                "recent_files": list(recent_files or []),
                "file_snapshot": self._snapshot_index(workspace_id),
            },
            sort_keys=True,
        )
        self._store.end_session(session_id, resume_state=state)
        self._store.append_audit(
            event="resume.session",
            outcome="closed",
            workspace_id=workspace_id,
            detail={"session_id": session_id, "had_note": bool(note)},
        )

    def _snapshot_index(self, workspace_id: int) -> dict[str, list]:
        """Path to [mtime, size], as the index currently sees the workspace."""
        return {
            row["rel_path"]: [row["mtime"], row["size"]]
            for row in self._store.list_files(workspace_id)
        }

    # -- replaying ---------------------------------------------------------

    def report(self, workspace_id: int) -> ResumeReport:
        """Build the picture of what happened while the user was away."""
        workspace = self._store.get_workspace(workspace_id)
        if workspace is None:
            return ResumeReport(
                workspace_id=workspace_id,
                workspace_name="unknown",
                last_seen=None,
                notes=("that workspace is no longer granted",),
            )

        name = workspace["name"]
        session = self._store.latest_session(workspace_id)
        if session is None or not session["ended_at"]:
            return ResumeReport(
                workspace_id=workspace_id,
                workspace_name=name,
                last_seen=None,
                open_proposals=self._open_proposals(workspace_id),
            )

        try:
            state = json.loads(session["resume_state"] or "{}")
        except json.JSONDecodeError:
            state = {}

        changes = self._diff_against(workspace_id, state.get("file_snapshot", {}))

        return ResumeReport(
            workspace_id=workspace_id,
            workspace_name=name,
            last_seen=_friendly(session["ended_at"]),
            note=str(state.get("note", "")),
            recent_files=tuple(state.get("recent_files", [])[:MAX_LISTED]),
            changes=changes,
            open_proposals=self._open_proposals(workspace_id),
            undoable_plans=self._undoable(workspace_id),
        )

    def _diff_against(
        self, workspace_id: int, snapshot: dict
    ) -> tuple[ChangedFile, ...]:
        """Compare the snapshot with the workspace as it is now.

        Reads the index rather than walking the disk, so this stays instant on
        a large folder. The watcher keeps the index current; if it is stale the
        report says less rather than saying something wrong.
        """
        current = {
            row["rel_path"]: (row["mtime"], row["size"])
            for row in self._store.list_files(workspace_id)
        }
        changes: list[ChangedFile] = []

        for rel_path, (mtime, size) in sorted(current.items()):
            previous = snapshot.get(rel_path)
            if previous is None:
                changes.append(ChangedFile(rel_path, "added", size))
            elif float(previous[0]) != float(mtime):
                changes.append(ChangedFile(rel_path, "modified", size))

        for rel_path in sorted(snapshot):
            if rel_path not in current:
                changes.append(ChangedFile(rel_path, "removed"))

        return tuple(changes)

    def _open_proposals(self, workspace_id: int) -> tuple[str, ...]:
        return tuple(
            row["description"]
            for row in self._store.list_rules(workspace_id, status="proposed")
        )

    def _undoable(self, workspace_id: int) -> tuple[str, ...]:
        rows = self._store.query(
            "SELECT DISTINCT plan_id FROM undo_journal WHERE workspace_id = ?"
            " ORDER BY id DESC LIMIT 5",
            (workspace_id,),
        )
        return tuple(row["plan_id"] for row in rows)

    # -- opening a file ----------------------------------------------------

    def resolve_for_opening(self, workspace_id: int, rel_path: str) -> Path | None:
        """Where a listed file actually is, or None if it is no longer reachable.

        Goes through the broker like everything else. A file listed in a resume
        report is not automatically reachable: the grant may have narrowed, or
        the path may now be deny-listed.
        """
        try:
            return self._broker.resolve(workspace_id, rel_path, Operation.READ).path
        except BoundaryRefusal:
            return None


def _friendly(timestamp: str) -> str:
    """An ISO timestamp as something a person would say."""
    try:
        when = datetime.fromisoformat(timestamp)
    except ValueError:
        return timestamp
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - when
    seconds = delta.total_seconds()
    if seconds < 90:
        return "a moment ago"
    if seconds < 3600:
        return f"{int(seconds // 60)} minutes ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return "an hour ago" if hours == 1 else f"{hours} hours ago"
    days = int(seconds // 86400)
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    return when.strftime("%d %B")
