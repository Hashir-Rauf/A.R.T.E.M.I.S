"""Answering a question about the user's files, with the stage gate applied."""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.answer import AnswerService
from artemis.core.broker import WorkspaceBroker
from artemis.core.context import ContextEngine
from artemis.core.indexer import Indexer
from artemis.core.providers import StubProvider
from artemis.core.router import ModelRouter
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store


@pytest.fixture
def workspace_id(manager: WorkspaceManager, sandbox: Path, indexer: Indexer) -> int:
    (sandbox / "notes" / "revenue.md").write_text("revenue grew 10%", encoding="utf-8")
    workspace = manager.grant(sandbox)
    indexer.scan(workspace.id)
    return workspace.id


def make_service(store: Store, broker: WorkspaceBroker, reply: str):
    router = ModelRouter(store=store)
    stub = StubProvider(replies=[reply])
    router.register(stub)
    return AnswerService(ContextEngine(store), broker, router), stub


def test_a_cited_claim_is_shown_with_its_file(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    service, _ = make_service(store, broker, "Revenue grew 10% [2].")
    answer = service.ask(workspace_id, "what did revenue say")
    assert "notes/revenue.md" in answer.text
    assert "[unsupported]" not in answer.text


def test_an_uncited_claim_is_marked_unsupported(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    reply = "Revenue grew 10% [2].\nThe CEO resigned in March."
    service, _ = make_service(store, broker, reply)
    answer = service.ask(workspace_id, "what did revenue say")
    assert "[unsupported] The CEO resigned in March." in answer.text


def test_the_model_is_given_the_file_text(
    store: Store, broker: WorkspaceBroker, workspace_id: int
) -> None:
    service, stub = make_service(store, broker, "Revenue grew 10% [2].")
    service.ask(workspace_id, "what did revenue say")
    assert "revenue grew 10%" in stub.calls[0]


def test_a_file_outside_the_grant_is_never_sent(
    store: Store,
    broker: WorkspaceBroker,
    workspace_id: int,
    sandbox: Path,
    outside: Path,
) -> None:
    (sandbox / "notes" / "secrets.md").symlink_to(outside / "secrets.txt")
    service, stub = make_service(store, broker, "I could not find it.")
    service.ask(workspace_id, "what is in secrets")
    assert "do not read" not in stub.calls[0]