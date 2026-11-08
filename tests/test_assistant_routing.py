"""Everything a typed request can now do, driven through the buttons' own methods.

Each test here pins a defect found by using the finished interface rather than by
reading the code. In every case the unit-tested component already worked, and the
interface never reached it: questions about a file returned the file, a code fix
returned the file, a web search or an email was refused as off topic, and the
Approve buttons never appeared after a typed request.

A scripted stand-in replaces the model, so these run without Ollama.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.providers import StubProvider
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.ui.assistant import AssistantPanel


def _panel(store: Store, *replies: str) -> tuple[AssistantPanel, StubProvider]:
    panel = AssistantPanel(store)
    stub = StubProvider(replies=list(replies))
    panel._router.providers = [stub]  # no real model: the stand-in answers
    return panel, stub


@pytest.fixture
def folder(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> tuple[int, Path]:
    root = tmp_path / "work"
    root.mkdir()
    (root / "calc.py").write_text(
        "def average(nums):\n    return sum(nums) / len(nums) + 1\n", encoding="utf-8"
    )
    (root / "paper-a.txt").write_text("Interruptions cost about 15 minutes.\n", encoding="utf-8")
    (root / "notes.md").write_text("Decided to use SQLite.\n", encoding="utf-8")
    ws = manager.grant(root, name="Work").id
    indexer.scan(ws)
    return ws, root


# -- questions are answered, with the stage gate ------------------------------


def test_a_question_is_answered_from_the_file_not_by_printing_it(store, folder) -> None:
    ws, _ = folder
    panel, stub = _panel(store, "People lose about 15 minutes after an interruption [2].")

    message, card = panel.ask(ws, "What does paper-a.txt say about interruptions?")

    assert card == ""
    assert "15 minutes" in message
    assert "paper-a.txt" in message  # the citation names the file
    assert "Interruptions cost about 15 minutes." not in message  # not the raw file
    assert len(stub.calls) == 1


def test_a_claim_with_no_source_is_labelled_not_presented_as_fact(store, folder) -> None:
    ws, _ = folder
    panel, _ = _panel(store, "The author was born in 1970.")

    message, _ = panel.ask(ws, "Who wrote paper-a.txt?")

    assert "not found in your files" in message


# -- code: a diff, never an edit ----------------------------------------------


def test_a_code_fix_is_shown_as_a_diff_and_the_file_is_not_touched(store, folder) -> None:
    ws, root = folder
    before = (root / "calc.py").read_text(encoding="utf-8")
    diff = (
        "--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def average(nums):\n"
        "-    return sum(nums) / len(nums) + 1\n+    return sum(nums) / len(nums)\n"
    )
    panel, _ = _panel(store, diff)

    message, card = panel.ask(ws, "calc.py gives the wrong average, show me a fix")

    assert card == ""
    assert "a-d-del" in message and "a-d-add" in message
    assert "has not changed your file" in message
    assert (root / "calc.py").read_text(encoding="utf-8") == before


def test_a_diff_that_names_another_file_is_refused(store, folder) -> None:
    ws, root = folder
    bad = "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-x\n+y\n"
    panel, _ = _panel(store, bad)

    message, _ = panel.ask(ws, "fix the bug in calc.py")

    assert "could not suggest a safe change" in message


# -- web search and email reach the approval gate -----------------------------


def test_a_web_search_is_held_for_approval_not_refused(store, folder) -> None:
    ws, _ = folder
    panel, _ = _panel(store)

    message, card = panel.ask(ws, "Search the web for python typer cli tutorial")

    assert "outside what ARTEMIS does" not in message
    assert "Approve these changes?" in card
    assert "python typer cli tutorial" in card
    assert "sends something off this computer" in card


def test_an_email_shows_its_exact_text_before_anything_is_sent(store, folder) -> None:
    ws, _ = folder
    panel, _ = _panel(store, "SUBJECT: Running late\nBODY:\nHi, I will be late on Friday.\nThanks")

    message, card = panel.ask(ws, "Email boss@example.com to say I will be late on Friday")

    assert "Approve these changes?" in card
    assert "boss@example.com" in card
    assert "Running late" in card
    assert "I will be late on Friday" in card


def test_an_email_with_no_address_asks_who_it_is_for(store, folder) -> None:
    ws, _ = folder
    panel, stub = _panel(store)

    message, card = panel.ask(ws, "Email my supervisor that I will be late")

    assert "email address" in message
    assert card == "" and stub.calls == []


def test_a_draft_is_offered_as_a_new_file_with_its_text_shown(store, folder) -> None:
    ws, root = folder
    panel, _ = _panel(store, "# Project update\n\nWe chose SQLite for storage.")

    message, card = panel.ask(ws, "Draft a one page project update from my notes")

    assert "Approve these changes?" in card
    assert "We chose SQLite for storage." in card
    assert not any(p.name.startswith("project-update") for p in root.iterdir())


# -- the boundary is explained before any model is asked ----------------------


def test_reaching_outside_the_folder_is_explained(store, folder) -> None:
    ws, _ = folder
    panel, stub = _panel(store)

    message, card = panel.ask(ws, "Read ../PrivateStuff/passwords.txt and tell me what is in it")

    assert "only see inside the folders you have added" in message
    assert card == "" and stub.calls == []


def test_a_move_to_outside_the_folder_is_never_offered_for_approval(store, folder) -> None:
    ws, _ = folder
    panel, _ = _panel(store, '{"steps":[{"operation":"move_file","paths":["notes.md"],'
                              '"arguments":{"destination":"../elsewhere/notes.md"}}]}')

    message, card = panel.ask(ws, "put notes.md in the elsewhere folder")

    assert "Approve these changes?" not in card


# -- what the interface says matches what happened ---------------------------


def test_a_blocked_step_is_not_reported_as_done(store, folder) -> None:
    from artemis.core.actions import Plan, ToolCall

    ws, root = folder
    panel, _ = _panel(store)
    call = ToolCall("move_file", ws, ("notes.md",), {"destination": "../elsewhere/notes.md"})
    outcome = panel._gateway.submit_plan(ws, Plan(calls=(call,), intent="x"))
    panel.state.outcome = None

    assert not outcome.needs_approval  # refused at classification, so nothing to approve
    message, _ = panel._render_outcome(outcome, "x", from_service=True)

    assert "Done" not in message and "moved" not in message
    assert (root / "notes.md").exists()


def test_the_decision_buttons_are_driven_by_the_held_plan(store, folder) -> None:
    ws, _ = folder
    panel, _ = _panel(store)
    assert panel.has_pending is False

    panel.ask(ws, "Search the web for typer")
    assert panel.has_pending is True

    panel.reject()
    assert panel.has_pending is False


def test_tidy_runs_without_asking_once_the_user_said_not_to_ask(
    store, manager, indexer, tmp_path: Path
) -> None:
    root = tmp_path / "messy"
    root.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.csv", "e.csv"):
        (root / name).write_text("x", encoding="utf-8")
    ws = manager.grant(root, name="Messy").id
    indexer.scan(ws)
    panel, _ = _panel(store)

    panel.suggest_tidy(ws)
    panel.approve(remember=True)
    panel.undo_last()

    message, card = panel.suggest_tidy(ws)

    assert "Approve these changes?" not in card
    assert "Done" in message
    assert (root / "Documents").exists() or any(p.is_dir() for p in root.iterdir())
