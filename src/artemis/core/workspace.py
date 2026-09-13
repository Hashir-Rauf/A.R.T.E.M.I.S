"""Workspace lifecycle: opting a folder in, and revoking it.

A grant is the only way ARTEMIS learns about anything on disk. Creating one is
therefore the moment the boundary is drawn, and the root is canonicalised here so
that every later containment test in the broker compares against a real location
rather than whatever the user happened to type.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from artemis.core.errors import WorkspaceError
from artemis.data import paths
from artemis.data.store import Store

PERMISSIONS = ("read_only", "read_write")
CLOUD_POLICIES = ("local_only", "cloud_allowed")


@dataclass(frozen=True)
class Workspace:
    """A granted folder, as the interface sees it."""

    id: int
    name: str
    root: Path
    permission: str
    cloud_policy: str
    created_at: str


class WorkspaceManager:
    """Creates, lists and revokes grants."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def grant(
        self,
        folder: Path | str,
        name: str | None = None,
        permission: str = "read_write",
        cloud_policy: str = "local_only",
    ) -> Workspace:
        """Opt a folder in as a workspace.

        The folder must already exist: ARTEMIS does not create the thing it is
        being granted access to. The root is stored canonically, so a grant made
        through a symlink is recorded against the real directory.
        """
        if permission not in PERMISSIONS:
            raise WorkspaceError(f"unknown permission: {permission}")
        if cloud_policy not in CLOUD_POLICIES:
            raise WorkspaceError(f"unknown cloud policy: {cloud_policy}")

        candidate = Path(folder).expanduser()
        if not candidate.exists():
            raise WorkspaceError(f"folder does not exist: {candidate}")
        if not candidate.is_dir():
            raise WorkspaceError(f"not a folder: {candidate}")

        root = candidate.resolve(strict=True)

        # ARTEMIS's own store must never become a workspace, or a grant could
        # read the audit log that records it.
        home = paths.artemis_home().resolve()
        if root == home or home in root.parents or root in home.parents:
            raise WorkspaceError("cannot grant the ARTEMIS store directory")

        existing = self._find_by_root(root)
        if existing is not None:
            raise WorkspaceError(f"already granted: {root}")

        workspace_id = self._store.create_workspace(
            name=name or root.name,
            root=root,
            permission=permission,
            cloud_policy=cloud_policy,
        )
        return self.get(workspace_id)  # type: ignore[return-value]

    def get(self, workspace_id: int) -> Workspace | None:
        row = self._store.get_workspace(workspace_id)
        return self._to_workspace(row) if row is not None else None

    def list(self) -> list[Workspace]:
        return [self._to_workspace(r) for r in self._store.list_workspaces()]

    def revoke(self, workspace_id: int) -> None:
        """Withdraw a grant. Cascades to everything derived from it.

        Nothing inside the user's folder is touched. Revoking removes what
        ARTEMIS knows, not what the user owns.
        """
        self._store.delete_workspace(workspace_id)

    # -- internals ---------------------------------------------------------

    def _find_by_root(self, root: Path) -> Workspace | None:
        for row in self._store.list_workspaces():
            if Path(row["root"]) == root:
                return self._to_workspace(row)
        return None

    @staticmethod
    def _to_workspace(row: object) -> Workspace:
        return Workspace(
            id=row["id"],  # type: ignore[index]
            name=row["name"],  # type: ignore[index]
            root=Path(row["root"]),  # type: ignore[index]
            permission=row["permission"],  # type: ignore[index]
            cloud_policy=row["cloud_policy"],  # type: ignore[index]
            created_at=row["created_at"],  # type: ignore[index]
        )
