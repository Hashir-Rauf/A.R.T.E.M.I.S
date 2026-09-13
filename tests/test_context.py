"""The Context Engine: what the model is allowed to see.

Two guarantees under test. Content from another workspace never reaches the
prompt, and every chunk keeps the tag that says where it came from. The second
is what makes the first survivable when something slips through: a passage from
a file arrives labelled as a file, so the planner treats it as material rather
than as instruction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.context import Chunk, ContextEngine, Provenance
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture
def engine(store: Store) -> ContextEngine:
    return ContextEngine(store)


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path) -> int:
    return manager.grant(sandbox).id


@pytest.fixture
def other_workspace_id(manager: WorkspaceManager, tmp_path: Path) -> int:
    folder = tmp_path / "somewhere-else"
    folder.mkdir()
    (folder / "private.txt").write_text("not yours", encoding="utf-8")
    return manager.grant(folder, name="Other").id


# -- the bounds assertion ------------------------------------------------------


def test_the_users_own_words_are_always_included(
    engine: ContextEngine, workspace_id: int
) -> None:
    context = engine.assemble(workspace_id, "summarise my notes")
    assert any(c.provenance is Provenance.USER for c in context.chunks)


def test_content_from_another_workspace_is_dropped(
    engine: ContextEngine, workspace_id: int, other_workspace_id: int
) -> None:
    context = engine.assemble(
        workspace_id,
        "summarise",
        retrieved=[
            Chunk("mine", Provenance.WORKSPACE_FILE, workspace_id, "notes/a.md"),
            Chunk("theirs", Provenance.WORKSPACE_FILE, other_workspace_id, "private.txt"),
        ],
    )

    assert context.dropped_out_of_scope == 1
    assert [c.source for c in context.chunks if c.source] == ["notes/a.md"]


def test_an_unlabelled_file_chunk_is_treated_as_out_of_scope(
    engine: ContextEngine, workspace_id: int
) -> None:
    """A file with no workspace is exactly what a leak would look like."""
    context = engine.assemble(
        workspace_id,
        "summarise",
        retrieved=[Chunk("mystery", Provenance.WORKSPACE_FILE, None, "mystery.txt")],
    )
    assert context.dropped_out_of_scope == 1


def test_dropping_out_of_scope_content_is_logged(
    engine: ContextEngine, workspace_id: int, other_workspace_id: int, store: Store
) -> None:
    """A silent drop would hide a retrieval bug."""
    engine.assemble(
        workspace_id,
        "summarise",
        retrieved=[
            Chunk("theirs", Provenance.WORKSPACE_FILE, other_workspace_id, "private.txt")
        ],
    )

    drops = [row for row in store.list_audit() if row["event"] == "context.bounds"]
    assert len(drops) == 1
    assert store.verify_audit_chain()


# -- provenance ----------------------------------------------------------------


def test_every_chunk_is_tagged_in_the_rendered_prompt(
    engine: ContextEngine, workspace_id: int
) -> None:
    """The tag survives into the prompt, which is what makes it useful."""
    context = engine.assemble(
        workspace_id,
        "summarise",
        retrieved=[
            Chunk("file text", Provenance.WORKSPACE_FILE, workspace_id, "notes/a.md")
        ],
    )
    rendered = context.render()

    assert "<user>" in rendered
    assert "workspace-file" in rendered


def test_a_citation_points_at_the_file_and_line(
    engine: ContextEngine, workspace_id: int
) -> None:
    context = engine.assemble(
        workspace_id,
        "summarise",
        retrieved=[
            Chunk(
                "text", Provenance.WORKSPACE_FILE, workspace_id, "notes/a.md",
                line_start=12,
            )
        ],
    )
    assert "notes/a.md:12" in context.citations.values()


# -- budgeting -----------------------------------------------------------------


def test_the_user_is_never_dropped_to_make_room(
    engine: ContextEngine, workspace_id: int
) -> None:
    """Losing the request to fit background material would be absurd."""
    big = [
        Chunk("x" * 4000, Provenance.WORKSPACE_FILE, workspace_id, f"f{i}.md", score=9)
        for i in range(5)
    ]
    context = engine.assemble(
        workspace_id, "this is the actual request", retrieved=big, token_budget=100
    )

    assert any(c.provenance is Provenance.USER for c in context.chunks)
    assert context.dropped_for_budget > 0


def test_higher_scoring_chunks_are_kept_first(
    engine: ContextEngine, workspace_id: int
) -> None:
    context = engine.assemble(
        workspace_id,
        "request",
        retrieved=[
            Chunk("x" * 300, Provenance.WORKSPACE_FILE, workspace_id, "low.md", score=1),
            Chunk("y" * 300, Provenance.WORKSPACE_FILE, workspace_id, "high.md", score=9),
        ],
        token_budget=120,
    )
    kept = [c.source for c in context.chunks if c.source]
    assert kept == ["high.md"]


def test_chunks_are_dropped_whole_rather_than_truncated(
    engine: ContextEngine, workspace_id: int
) -> None:
    """Half a passage under a citation points at something never seen."""
    original = "y" * 900
    context = engine.assemble(
        workspace_id,
        "request",
        retrieved=[
            Chunk(original, Provenance.WORKSPACE_FILE, workspace_id, "a.md", score=5)
        ],
        token_budget=10_000,
    )
    kept = next(c for c in context.chunks if c.source == "a.md")
    assert kept.text == original


# -- retrieval -----------------------------------------------------------------


def test_index_search_only_returns_files_from_this_workspace(
    engine: ContextEngine, indexer, workspace_id: int, other_workspace_id: int
) -> None:
    indexer.scan(workspace_id)
    indexer.scan(other_workspace_id)

    chunks = engine.chunks_from_index(workspace_id, "readme")

    assert chunks
    assert all(c.workspace_id == workspace_id for c in chunks)
    assert all(c.provenance is Provenance.WORKSPACE_FILE for c in chunks)
