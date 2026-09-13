"""The Workspace Broker.

The single component that turns a logical reference into a real filesystem path,
and the enforcement point for bounded scope on the write side (Architecture
Section 6.1). Every capability service resolves through here; none touches the
filesystem directly.

The five assertions, in the order the architecture specifies:

    1. resolve against the active grant root
    2. canonicalise (realpath, resolving symlinks)
    3. assert the canonical path is under the grant root
    4. assert not in the deny-list (system, hidden, credential paths)
    5. assert the operation is within the granted permission

Step 2 before step 3 is the whole point. Canonicalising first is what makes a
symlink pointing outside the grant, or a `..` segment climbing out of it, resolve
to its true location before containment is tested. Asserting first and resolving
afterwards would accept a path that merely looks contained. That ordering is the
difference between a boundary and a suggestion, so it is covered directly by the
Sprint 2 stage gate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePath

from artemis.core.errors import BoundaryRefusal, RefusalReason
from artemis.data.store import Store


class Operation(str, Enum):
    """What a caller intends to do with the resolved path."""

    READ = "read"
    WRITE = "write"


# Permission levels a grant may carry, and the operations each admits.
_PERMITS: dict[str, frozenset[Operation]] = {
    "read_only": frozenset({Operation.READ}),
    "read_write": frozenset({Operation.READ, Operation.WRITE}),
}

# Path segments never resolvable inside a workspace, whatever the grant says.
# A user may well opt in a folder that happens to contain one of these; the grant
# covers the folder, not these.
_DENIED_NAMES = frozenset(
    {
        ".ssh",
        ".gnupg",
        ".aws",
        ".azure",
        ".kube",
        ".docker",
        ".git-credentials",
        ".netrc",
        "_netrc",
        ".htpasswd",
        ".env",
        "id_rsa",
        "id_ed25519",
        "credentials",
        "secrets.json",
    }
)

# ARTEMIS's own store is never reachable through a workspace grant, even if the
# user opts in a parent of it. Otherwise a workspace could read its own audit log.
_DENIED_DIRS = frozenset({".artemis"})


@dataclass(frozen=True)
class Resolved:
    """A path that passed every assertion.

    Holding a Resolved is the proof that the boundary was checked. Services take
    this rather than a bare Path so that an unchecked path cannot reach the
    filesystem by accident.
    """

    path: Path
    workspace_id: int
    rel_path: str
    operation: Operation


class WorkspaceBroker:
    """Resolves workspace-relative references, or refuses.

    The broker logs every refusal to the audit log before raising, so an attempt
    to leave the boundary is recorded whether or not the caller handles it.
    """

    def __init__(self, store: Store) -> None:
        self._store = store

    # -- public API --------------------------------------------------------

    def resolve(
        self,
        workspace_id: int,
        reference: str | PurePath,
        operation: Operation = Operation.READ,
    ) -> Resolved:
        """Resolve `reference` inside `workspace_id`, or raise BoundaryRefusal."""
        reference = str(reference)
        row = self._store.get_workspace(workspace_id)
        if row is None:
            raise self._refuse(
                RefusalReason.NO_ACTIVE_GRANT,
                reference,
                workspace_id,
                "no grant covers this workspace id",
            )

        grant_root = Path(row["root"])

        # 1. Resolve against the grant root. An absolute reference is rejected
        #    rather than honoured: references are always workspace-relative, so
        #    an absolute one indicates a caller that has not understood the
        #    contract.
        candidate = Path(reference)
        if candidate.is_absolute():
            raise self._refuse(
                RefusalReason.OUTSIDE_GRANT,
                reference,
                workspace_id,
                "reference must be workspace-relative",
            )
        candidate = grant_root / candidate

        # 2. Canonicalise. strict=False so a path that does not exist yet (a file
        #    about to be written) still resolves; its parent chain is still
        #    followed, so a symlinked parent cannot smuggle the target outside.
        try:
            real = candidate.resolve(strict=False)
            real_root = grant_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:  # RuntimeError: symlink loop
            raise self._refuse(
                RefusalReason.UNRESOLVABLE,
                reference,
                workspace_id,
                type(exc).__name__,
            ) from exc

        # 3. Containment, tested on the canonical path.
        if not self._is_within(real, real_root):
            raise self._refuse(
                RefusalReason.OUTSIDE_GRANT,
                reference,
                workspace_id,
                "canonical path resolved outside the grant root",
            )

        # 4. Deny-list, tested on the portion inside the workspace.
        rel = real.relative_to(real_root)
        denied = self._denied_segment(rel)
        if denied is not None:
            raise self._refuse(
                RefusalReason.DENY_LISTED,
                reference,
                workspace_id,
                f"denied path segment: {denied}",
            )

        # 5. Permission.
        permitted = _PERMITS.get(row["permission"], frozenset())
        if operation not in permitted:
            raise self._refuse(
                RefusalReason.PERMISSION_EXCEEDED,
                reference,
                workspace_id,
                f"{operation.value} exceeds {row['permission']}",
            )

        return Resolved(
            path=real,
            workspace_id=workspace_id,
            rel_path=rel.as_posix(),
            operation=operation,
        )

    def is_within_grant(self, workspace_id: int, absolute: Path) -> bool:
        """Whether an absolute path lies inside a grant, without raising.

        Used by the file watcher, which sees absolute paths from the operating
        system and must filter them rather than treat each one as a refusal.
        """
        row = self._store.get_workspace(workspace_id)
        if row is None:
            return False
        try:
            real = absolute.resolve(strict=False)
            real_root = Path(row["root"]).resolve(strict=True)
        except (OSError, RuntimeError):
            return False
        if not self._is_within(real, real_root):
            return False
        return self._denied_segment(real.relative_to(real_root)) is None

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        """True when `path` is `root` or lies beneath it.

        Uses os.path.commonpath rather than a string prefix test, so that a
        sibling directory sharing a name prefix (``/data/ws-evil`` against a grant
        on ``/data/ws``) is not mistaken for a child.
        """
        try:
            return os.path.commonpath([str(path), str(root)]) == str(root)
        except ValueError:
            # Different drives on Windows, or a mix of absolute and relative.
            return False

    @staticmethod
    def _denied_segment(rel: PurePath) -> str | None:
        """The first deny-listed segment in `rel`, or None."""
        for part in rel.parts:
            lowered = part.lower()
            if lowered in _DENIED_DIRS or lowered in _DENIED_NAMES:
                return part
        return None

    def _refuse(
        self,
        reason: RefusalReason,
        requested: str,
        workspace_id: int | None,
        detail: str,
    ) -> BoundaryRefusal:
        """Log the refusal, then build the exception for the caller to raise."""
        self._store.append_audit(
            event="broker.resolve",
            outcome="refused",
            workspace_id=workspace_id,
            detail={"requested": requested, "reason": reason.value, "note": detail},
        )
        return BoundaryRefusal(reason, requested, workspace_id, detail)
