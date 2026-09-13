"""Sprint 2 stage gate: traversal and symlink escapes are refused and logged.

These are the tests the sprint is judged on. Everything else in Sprint 2 exists so
that these can pass and keep passing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from artemis.core.broker import Operation, WorkspaceBroker
from artemis.core.errors import BoundaryRefusal, RefusalReason
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


def _can_symlink() -> bool:
    """Whether this machine can create symlinks.

    Asked as a capability question rather than a platform one. Windows does allow
    symlinks under Developer Mode or an elevated shell, and skipping on platform
    alone would silently disable the most important test in this sprint on the
    very machine the project is developed on.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "target"
        target.mkdir()
        try:
            (root / "link").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
        return True


CAN_SYMLINK = _can_symlink()


def test_resolves_a_reference_inside_the_grant(
    manager: WorkspaceManager, broker: WorkspaceBroker, sandbox: Path
) -> None:
    ws = manager.grant(sandbox)
    resolved = broker.resolve(ws.id, "notes/chapter3.md")
    assert resolved.path == (sandbox / "notes" / "chapter3.md").resolve()
    assert resolved.rel_path == "notes/chapter3.md"


# -- the stage gate ------------------------------------------------------------


@pytest.mark.parametrize(
    "reference",
    [
        "../private/secrets.txt",
        "../../etc/passwd",
        "notes/../../private/secrets.txt",
        "./../../private",
    ],
)
def test_relative_traversal_is_refused(
    manager: WorkspaceManager,
    broker: WorkspaceBroker,
    sandbox: Path,
    reference: str,
) -> None:
    """A `..` segment that climbs out of the grant must be refused."""
    ws = manager.grant(sandbox)
    with pytest.raises(BoundaryRefusal) as caught:
        broker.resolve(ws.id, reference)
    assert caught.value.reason is RefusalReason.OUTSIDE_GRANT


@pytest.mark.skipif(
    not CAN_SYMLINK, reason="this machine cannot create symlinks"
)
def test_symlink_pointing_outside_is_refused(
    manager: WorkspaceManager,
    broker: WorkspaceBroker,
    sandbox: Path,
    outside: Path,
) -> None:
    """A symlink inside the grant that points out of it must be refused.

    This is the case that canonicalising before the bounds check exists to catch:
    the link's own path looks contained, and only its resolved target does not.
    """
    (sandbox / "escape").symlink_to(outside, target_is_directory=True)
    ws = manager.grant(sandbox)
    with pytest.raises(BoundaryRefusal) as caught:
        broker.resolve(ws.id, "escape/secrets.txt")
    assert caught.value.reason is RefusalReason.OUTSIDE_GRANT


def test_every_refusal_is_written_to_the_audit_log(
    manager: WorkspaceManager, broker: WorkspaceBroker, sandbox: Path, store: Store
) -> None:
    """A refusal is recorded whether or not the caller handles it."""
    ws = manager.grant(sandbox)
    with pytest.raises(BoundaryRefusal):
        broker.resolve(ws.id, "../private/secrets.txt")

    refusals = [
        row
        for row in store.list_audit()
        if row["event"] == "broker.resolve" and row["outcome"] == "refused"
    ]
    assert len(refusals) == 1
    assert "../private/secrets.txt" in refusals[0]["detail"]
    assert store.verify_audit_chain()


# -- the remaining assertions --------------------------------------------------


def test_absolute_references_are_refused(
    manager: WorkspaceManager, broker: WorkspaceBroker, sandbox: Path, outside: Path
) -> None:
    ws = manager.grant(sandbox)
    with pytest.raises(BoundaryRefusal) as caught:
        broker.resolve(ws.id, str(outside / "secrets.txt"))
    assert caught.value.reason is RefusalReason.OUTSIDE_GRANT


def test_deny_listed_segments_are_refused(
    manager: WorkspaceManager, broker: WorkspaceBroker, sandbox: Path
) -> None:
    """Credential paths stay unreachable even inside a granted folder."""
    (sandbox / ".ssh").mkdir()
    (sandbox / ".ssh" / "id_rsa").write_text("key", encoding="utf-8")
    ws = manager.grant(sandbox)
    with pytest.raises(BoundaryRefusal) as caught:
        broker.resolve(ws.id, ".ssh/id_rsa")
    assert caught.value.reason is RefusalReason.DENY_LISTED


def test_write_is_refused_on_a_read_only_grant(
    manager: WorkspaceManager, broker: WorkspaceBroker, sandbox: Path
) -> None:
    ws = manager.grant(sandbox, permission="read_only")
    assert broker.resolve(ws.id, "readme.txt", Operation.READ)
    with pytest.raises(BoundaryRefusal) as caught:
        broker.resolve(ws.id, "readme.txt", Operation.WRITE)
    assert caught.value.reason is RefusalReason.PERMISSION_EXCEEDED


def test_unknown_workspace_is_refused(broker: WorkspaceBroker) -> None:
    with pytest.raises(BoundaryRefusal) as caught:
        broker.resolve(999, "anything.txt")
    assert caught.value.reason is RefusalReason.NO_ACTIVE_GRANT


def test_sibling_directory_sharing_a_prefix_is_not_inside(
    manager: WorkspaceManager, broker: WorkspaceBroker, tmp_path: Path
) -> None:
    """`/data/ws-evil` must not count as inside a grant on `/data/ws`.

    A naive string-prefix containment test passes this by mistake.
    """
    granted = tmp_path / "ws"
    granted.mkdir()
    sibling = tmp_path / "ws-evil"
    sibling.mkdir()
    (sibling / "loot.txt").write_text("x", encoding="utf-8")

    ws = manager.grant(granted)
    with pytest.raises(BoundaryRefusal):
        broker.resolve(ws.id, "../ws-evil/loot.txt")
    assert not broker.is_within_grant(ws.id, sibling / "loot.txt")


def test_a_path_that_does_not_exist_yet_still_resolves(
    manager: WorkspaceManager, broker: WorkspaceBroker, sandbox: Path
) -> None:
    """Writing a new file must be possible; the boundary still applies."""
    ws = manager.grant(sandbox)
    resolved = broker.resolve(ws.id, "notes/new-file.md", Operation.WRITE)
    assert not resolved.path.exists()
    assert resolved.rel_path == "notes/new-file.md"
