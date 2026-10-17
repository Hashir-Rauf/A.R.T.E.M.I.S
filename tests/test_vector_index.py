"""The vector index: search by meaning, kept inside the boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.broker import WorkspaceBroker
from artemis.core.embedder import FakeEmbedder
from artemis.core.indexer import Indexer
from artemis.core.vector_index import VectorIndex
from artemis.core.workspace import WorkspaceManager
from artemis.data import paths
from artemis.data.store import Store


class CountingEmbedder(FakeEmbedder):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return super().embed(text)


@pytest.fixture
def embedder() -> CountingEmbedder:
    return CountingEmbedder()


@pytest.fixture
def index(store: Store, broker: WorkspaceBroker, embedder: CountingEmbedder) -> VectorIndex:
    return VectorIndex(store, broker, embedder)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path, indexer: Indexer) -> int:
    (sandbox / "notes" / "revenue.md").write_text("revenue grew 10% this year", encoding="utf-8")
    (sandbox / "notes" / "cats.md").write_text("the cat sat on the mat", encoding="utf-8")
    workspace = manager.grant(sandbox)
    indexer.scan(workspace.id)
    return workspace.id


def test_search_finds_the_file_that_matches_by_meaning(
    index: VectorIndex, workspace_id: int
) -> None:
    index.index_workspace(workspace_id)
    results = index.search(workspace_id, "how much did revenue grow")
    assert results[0].source == "notes/revenue.md"
    assert results[0].line_start == 1


def test_a_second_run_embeds_nothing_new(
    index: VectorIndex, workspace_id: int, embedder: CountingEmbedder
) -> None:
    index.index_workspace(workspace_id)
    before = embedder.calls
    assert index.index_workspace(workspace_id) == 0
    assert embedder.calls == before


def test_changing_one_line_embeds_only_the_changed_chunk(
    index: VectorIndex, workspace_id: int, sandbox: Path, embedder: CountingEmbedder
) -> None:
    lines = [f"line number {n} " + "x" * 40 for n in range(1, 41)]
    big = sandbox / "notes" / "big.md"
    big.write_text("\n".join(lines), encoding="utf-8")
    Indexer(index.store, index.broker).scan(workspace_id)
    first = index.index_file(workspace_id, "notes/big.md")
    assert first > 2
    lines[-1] = "a different last line"
    big.write_text("\n".join(lines), encoding="utf-8")
    assert index.index_file(workspace_id, "notes/big.md") == 1


def test_a_deleted_file_leaves_the_index(
    index: VectorIndex, workspace_id: int, sandbox: Path
) -> None:
    index.index_workspace(workspace_id)
    (sandbox / "notes" / "cats.md").unlink()
    Indexer(index.store, index.broker).scan(workspace_id)
    index.index_workspace(workspace_id)
    results = index.search(workspace_id, "cat mat")
    assert all(r.source != "notes/cats.md" for r in results)


def test_a_file_outside_the_grant_is_never_embedded(
    index: VectorIndex, workspace_id: int, sandbox: Path, outside: Path, embedder: CountingEmbedder
) -> None:
    link = sandbox / "notes" / "escape.md"
    link.symlink_to(outside / "secrets.txt")
    assert index.index_file(workspace_id, "notes/escape.md") == 0
    assert index.search(workspace_id, "do not read") == []


def test_one_workspace_cannot_search_another(
    index: VectorIndex, workspace_id: int, manager: WorkspaceManager, tmp_path: Path
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    (other / "plans.md").write_text("secret launch plans", encoding="utf-8")
    other_id = manager.grant(other, name="Other").id
    Indexer(index.store, index.broker).scan(other_id)
    index.index_workspace(workspace_id)
    index.index_workspace(other_id)
    mine = index.search(workspace_id, "secret launch plans")
    assert all(r.source != "plans.md" for r in mine)
    assert index.search(other_id, "secret launch plans")[0].source == "plans.md"


def test_revoking_a_workspace_deletes_its_index(
    index: VectorIndex, workspace_id: int, manager: WorkspaceManager
) -> None:
    index.index_workspace(workspace_id)
    assert (paths.index_dir(workspace_id) / "vectors.db").exists()
    manager.revoke(workspace_id)
    assert not paths.index_dir(workspace_id).exists()