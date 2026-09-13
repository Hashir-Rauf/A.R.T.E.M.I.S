"""Sprint 2 stories one and three: granting a folder, and the file index.

Includes the cascade test, which is what makes the delete claim in the disclosure
panel falsifiable rather than merely stated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.disclosure import DisclosurePanel
from artemis.core.errors import WorkspaceError
from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data import paths
from artemis.data.store import Store


def test_granting_a_folder_records_a_canonical_root(
    manager: WorkspaceManager, sandbox: Path
) -> None:
    ws = manager.grant(sandbox, name="Thesis")
    assert ws.name == "Thesis"
    assert ws.root == sandbox.resolve()
    assert ws.permission == "read_write"
    assert ws.cloud_policy == "local_only"  # local-first by default


def test_granting_a_missing_folder_fails(manager: WorkspaceManager, tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError):
        manager.grant(tmp_path / "nope")


def test_the_same_folder_cannot_be_granted_twice(
    manager: WorkspaceManager, sandbox: Path
) -> None:
    manager.grant(sandbox)
    with pytest.raises(WorkspaceError):
        manager.grant(sandbox)


def test_the_artemis_store_cannot_be_granted(
    manager: WorkspaceManager, artemis_home: Path
) -> None:
    """Otherwise a workspace could read the audit log that records it."""
    with pytest.raises(WorkspaceError):
        manager.grant(artemis_home)


def test_scan_indexes_only_files_inside_the_grant(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    ws = manager.grant(sandbox)
    count = indexer.scan(ws.id)
    indexed = {row["rel_path"] for row in store.list_files(ws.id)}
    assert count == 2
    assert indexed == {"readme.txt", "notes/chapter3.md"}


def test_scan_skips_deny_listed_paths(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    (sandbox / ".ssh").mkdir()
    (sandbox / ".ssh" / "id_rsa").write_text("key", encoding="utf-8")
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    indexed = {row["rel_path"] for row in store.list_files(ws.id)}
    assert not any(p.startswith(".ssh") for p in indexed)


def test_scan_drops_rows_for_deleted_files(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    (sandbox / "readme.txt").unlink()
    indexer.scan(ws.id)
    indexed = {row["rel_path"] for row in store.list_files(ws.id)}
    assert indexed == {"notes/chapter3.md"}


def test_index_records_a_content_hash(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    row = next(r for r in store.list_files(ws.id) if r["rel_path"] == "readme.txt")
    assert row["content_hash"] is not None
    assert row["file_type"] == "txt"


def test_revoking_a_workspace_cascades(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    """Deletion is a real cascade: rows and the index directory both go."""
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    index_directory = paths.index_dir(ws.id)
    index_directory.mkdir(parents=True, exist_ok=True)
    (index_directory / "vectors.bin").write_bytes(b"embedding")

    assert store.count_files(ws.id) == 2
    manager.revoke(ws.id)

    assert store.get_workspace(ws.id) is None
    assert store.list_files(ws.id) == []
    assert not index_directory.exists()


def test_revoking_leaves_the_users_files_alone(
    manager: WorkspaceManager, indexer: Indexer, sandbox: Path
) -> None:
    """ARTEMIS forgets. It does not delete what it was shown."""
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    manager.revoke(ws.id)
    assert (sandbox / "readme.txt").exists()
    assert (sandbox / "notes" / "chapter3.md").exists()


def test_disclosure_panel_reports_what_is_held(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    snapshot = DisclosurePanel(store).snapshot()
    rows = {r.label: r for r in snapshot.rows}

    assert rows["Workspaces granted"].count == 1
    assert rows["Files indexed"].count == 2
    assert rows["Actions recorded"].count > 0
    # A log the subject can erase is not an audit log.
    assert rows["Actions recorded"].deletable is False


def test_forgetting_one_file_leaves_it_on_disk(
    manager: WorkspaceManager, indexer: Indexer, store: Store, sandbox: Path
) -> None:
    ws = manager.grant(sandbox)
    indexer.scan(ws.id)
    DisclosurePanel(store).forget_file(ws.id, "readme.txt")
    assert store.count_files(ws.id) == 1
    assert (sandbox / "readme.txt").exists()


def test_audit_chain_detects_tampering(
    manager: WorkspaceManager, store: Store, sandbox: Path
) -> None:
    manager.grant(sandbox)
    assert store.verify_audit_chain()
    with store._write() as conn:  # noqa: SLF001 - deliberately tampering
        conn.execute("UPDATE audit_log SET outcome = 'forged' WHERE id = 1")
    assert not store.verify_audit_chain()
