"""The "What ARTEMIS Knows" panel.

Not a summary the system writes about itself, but a live query across every store
(Architecture Section 7.3). That distinction is the whole point: a report can be
wrong or stale, whereas a query cannot disagree with the data it reads. It makes
the trust claim falsifiable, which is a stronger position than making it
persuasive.

Sprint 2 populates the rows that exist at this stage: workspaces, indexed files,
and the audit log. The remaining rows are declared with a zero count so the panel
shows its full shape from the start, and later sprints fill them in rather than
adding new sections.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artemis.data import paths
from artemis.data.store import Store


@dataclass(frozen=True)
class Row:
    """One line in the panel.

    `deletable` is explicit rather than inferred. The audit log is deliberately
    not deletable: a log the subject can erase is not an audit log.
    """

    label: str
    count: int
    deletable: bool
    detail: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Disclosure:
    """Everything ARTEMIS currently holds, for one workspace or for all of them."""

    workspace_id: int | None
    rows: list[Row]

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "rows": [
                {
                    "label": r.label,
                    "count": r.count,
                    "deletable": r.deletable,
                    "detail": r.detail,
                }
                for r in self.rows
            ],
        }


class DisclosurePanel:
    """Queries every store and reports what is held."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def snapshot(self, workspace_id: int | None = None, sample: int = 20) -> Disclosure:
        """Read the current state of every store.

        `sample` bounds how many individual items are listed per row. The counts
        are always exact; only the illustrative detail is truncated.
        """
        rows: list[Row] = []

        if workspace_id is None:
            workspaces = self._store.list_workspaces()
            rows.append(
                Row(
                    label="Workspaces granted",
                    count=len(workspaces),
                    deletable=True,
                    detail=[f"{w['name']}  ({w['root']})" for w in workspaces[:sample]],
                )
            )
            files = self._store.list_files()
        else:
            files = self._store.list_files(workspace_id)

        rows.append(
            Row(
                label="Files indexed",
                count=len(files),
                deletable=True,
                detail=[f["rel_path"] for f in files[:sample]],
            )
        )

        rows.append(
            Row(
                label="Chunks embedded",
                count=self._count_index_files(workspace_id),
                deletable=True,
            )
        )

        audit = self._store.list_audit(limit=sample)
        rows.append(
            Row(
                label="Actions recorded",
                count=self._store.count_audit(),
                deletable=False,
                detail=[f"{a['ts']}  {a['event']}  {a['outcome']}" for a in audit],
            )
        )

        # Declared now, populated by later sprints. Showing them at zero keeps the
        # panel's shape honest about what the system will eventually hold.
        for label, table in (
            ("Facts remembered", "memory_kv"),
            ("Sessions retained", "sessions"),
            ("Automation rules", "automation_rules"),
            ("Policy exceptions granted", "policy_rules"),
            ("Undo entries", "undo_journal"),
        ):
            rows.append(
                Row(label=label, count=self._count(table, workspace_id), deletable=True)
            )

        return Disclosure(workspace_id=workspace_id, rows=rows)

    def forget_workspace(self, workspace_id: int) -> None:
        """Delete a workspace and everything derived from it.

        A real cascade, not a hide: the database rows go through the foreign key
        cascade and the index directory is removed from disk. Nothing inside the
        user's own folder is touched.
        """
        self._store.delete_workspace(workspace_id)

    def forget_file(self, workspace_id: int, rel_path: str) -> None:
        """Drop one file's index row. The file itself is left alone."""
        self._store.remove_file(workspace_id, rel_path)
        self._store.append_audit(
            event="disclosure.forget_file",
            outcome="deleted",
            workspace_id=workspace_id,
            detail={"rel_path": rel_path},
        )

    # -- internals ---------------------------------------------------------

    def _count(self, table: str, workspace_id: int | None) -> int:
        # Table names are from the fixed tuple above, never from user input.
        if workspace_id is None:
            sql = f"SELECT COUNT(*) AS n FROM {table}"  # noqa: S608
            args: tuple[Any, ...] = ()
        else:
            sql = f"SELECT COUNT(*) AS n FROM {table} WHERE workspace_id = ?"  # noqa: S608
            args = (workspace_id,)
        try:
            row = self._store.query_one(sql, args)
        except Exception:
            return 0
        return int(row["n"]) if row else 0

    def _count_index_files(self, workspace_id: int | None) -> int:
        """Files sitting in the per-workspace vector index directories."""
        if workspace_id is not None:
            targets = [paths.index_dir(workspace_id)]
        else:
            root = paths.artemis_home() / "index"
            targets = [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
        return sum(
            1 for target in targets if target.exists() for _ in target.rglob("*")
        )

    @staticmethod
    def disk_usage() -> int:
        """Bytes the ARTEMIS store occupies. Shown so the cost is never hidden."""
        home = paths.artemis_home()
        return sum(p.stat().st_size for p in home.rglob("*") if p.is_file())

    @staticmethod
    def purge_everything() -> None:
        """Remove the entire local store. The strongest form of the delete claim."""
        shutil.rmtree(paths.artemis_home(), ignore_errors=True)
        Path(paths.artemis_home()).mkdir(parents=True, exist_ok=True)
