"""The assistant surface: the first point where a person can drive the gates.

These tests exist because of a pattern this project has hit twice already: a
component works, its tests pass, and the button that calls it does nothing. So
everything here goes through the methods the buttons are actually wired to.

The most important test is `test_approving_is_what_makes_it_run`. Four sprints
of machinery exist to make that one assertion true from a user's point of view:
the plan is visible, nothing happens, and then the person decides.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.ui.assistant import AssistantPanel


@pytest.fixture
def assistant(store: Store) -> AssistantPanel:
    return AssistantPanel(store)


@pytest.fixture
def messy(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> int:
    folder = tmp_path / "messy"
    folder.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf", "d.csv", "e.csv"):
        (folder / name).write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Messy").id
    indexer.scan(workspace_id)
    return workspace_id


def _root(store: Store, workspace_id: int) -> Path:
    return Path(store.get_workspace(workspace_id)["root"])


# -- the approval flow ---------------------------------------------------------


def test_a_tidy_is_offered_and_nothing_happens_yet(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The plan is shown. The folder is untouched."""
    before = sorted(p.name for p in _root(store, messy).iterdir())

    message, card = assistant.suggest_tidy(messy)

    assert "Would move" in message
    assert "Approve these changes?" in card
    assert "Nothing has happened yet" in card
    assert sorted(p.name for p in _root(store, messy).iterdir()) == before


def test_the_card_says_what_will_not_happen(
    assistant: AssistantPanel, messy: int
) -> None:
    """The reassuring facts are what let a person answer quickly."""
    _, card = assistant.suggest_tidy(messy)

    assert "Nothing is deleted" in card
    assert "Nothing leaves this computer" in card
    assert "You can undo this afterwards" in card


def test_every_step_is_listed_not_summarised(
    assistant: AssistantPanel, messy: int
) -> None:
    """Approving 'tidy my folder' would make the approval meaningless."""
    _, card = assistant.suggest_tidy(messy)

    assert card.count('class="a-step"') == 7  # 2 folders + 5 moves


def test_approving_is_what_makes_it_run(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The assertion four sprints of machinery exist to support."""
    root = _root(store, messy)
    assistant.suggest_tidy(messy)

    assert (root / "a.pdf").exists(), "nothing should have happened yet"

    message, card = assistant.approve()

    assert "Done" in message
    assert card == "", "the card must be cleared once answered"
    assert (root / "Documents" / "a.pdf").exists()
    assert not (root / "a.pdf").exists()


def test_rejecting_changes_nothing(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    root = _root(store, messy)
    assistant.suggest_tidy(messy)

    message, card = assistant.reject()

    assert "Left alone" in message
    assert card == ""
    assert (root / "a.pdf").exists()
    assert not (root / "Documents").exists()


def test_a_rejected_plan_cannot_then_be_approved(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """Answering clears the held turn, so the buttons cannot both apply."""
    assistant.suggest_tidy(messy)
    assistant.reject()

    message, _ = assistant.approve()

    assert "nothing waiting" in message
    assert not (_root(store, messy) / "Documents").exists()


def test_approving_with_remember_says_so(
    assistant: AssistantPanel, messy: int
) -> None:
    assistant.suggest_tidy(messy)
    message, _ = assistant.approve(remember=True)

    assert "will not ask again" in message


def test_approving_nothing_is_reported_not_crashed(
    assistant: AssistantPanel,
) -> None:
    message, card = assistant.approve()
    assert "nothing waiting" in message
    assert card == ""


# -- undo ----------------------------------------------------------------------


def test_undo_puts_the_files_back(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    root = _root(store, messy)
    before = sorted(p.name for p in root.iterdir())

    assistant.suggest_tidy(messy)
    assistant.approve()
    message = assistant.undo_last()

    assert "Undone" in message
    assert sorted(p.name for p in root.iterdir()) == before


def test_undo_with_nothing_to_undo_says_so(assistant: AssistantPanel) -> None:
    assert "nothing to undo" in assistant.undo_last()


def test_undo_is_offered_only_after_something_ran(
    assistant: AssistantPanel, messy: int
) -> None:
    assert assistant.can_undo is False

    assistant.suggest_tidy(messy)
    assert assistant.can_undo is False, "proposing is not doing"

    assistant.approve()
    assert assistant.can_undo is True


# -- resume and patterns -------------------------------------------------------


def test_resume_reports_what_changed(
    assistant: AssistantPanel, messy: int, indexer: Indexer
) -> None:
    assistant.suggest_tidy(messy)
    assistant.approve()
    indexer.scan(messy)

    html = assistant.resume_html(messy)

    assert "a-resume" in html
    assert "first time" in html or "new" in html


def test_patterns_are_offered_never_applied(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The feature's whole point: it asks, it does not act."""
    assistant.suggest_tidy(messy)
    assistant.approve()

    message = assistant.look_for_patterns(messy)

    assert "will not act" in message or "Nothing repeated" in message
    assert store.list_rules(messy, status="accepted") == []


def test_an_already_tidy_folder_is_not_nagged(
    assistant: AssistantPanel, manager: WorkspaceManager, indexer: Indexer,
    tmp_path: Path,
) -> None:
    folder = tmp_path / "tidy"
    folder.mkdir()
    (folder / "only.txt").write_text("x", encoding="utf-8")
    workspace_id = manager.grant(folder, name="Tidy").id
    indexer.scan(workspace_id)

    message, card = assistant.suggest_tidy(workspace_id)

    assert "tidy enough" in message
    assert card == ""


# -- guard rails ---------------------------------------------------------------


def test_asking_without_a_folder_is_explained(assistant: AssistantPanel) -> None:
    message, card = assistant.ask(None, "tidy up")
    assert "Choose a folder" in message
    assert card == ""


def test_asking_nothing_is_explained(assistant: AssistantPanel, messy: int) -> None:
    message, _ = assistant.ask(messy, "   ")
    assert "Type what" in message


def test_a_workspace_name_is_escaped_into_the_card(
    assistant: AssistantPanel, messy: int, store: Store
) -> None:
    """The card is raw HTML, so anything interpolated must be escaped."""
    with store._write() as conn:  # noqa: SLF001 - seeding a hostile value
        conn.execute(
            "UPDATE workspaces SET name = ? WHERE id = ?",
            ("<script>alert(1)</script>", messy),
        )

    _, card = assistant.suggest_tidy(messy)

    assert "<script>" not in card
    assert "&lt;script&gt;" in card


# -- streaming and fast paths --------------------------------------------------
#
# The complaint these answer was that the page froze for about sixteen seconds
# and then showed a planner diagnostic. Two of the three fixes avoid the model
# altogether, because the fastest request is the one never sent.


def test_streaming_yields_progress_before_the_answer(
    assistant: AssistantPanel, messy: int
) -> None:
    """The caller gets something to show before the turn has finished."""
    frames = list(assistant.ask_streaming(messy, "move my pdfs into a folder"))
    assert len(frames) >= 2
    assert "a-thinking" in frames[0][0]
    assert "a-thinking" not in frames[-1][0]


def test_streaming_and_blocking_agree_on_the_outcome(
    assistant: AssistantPanel, messy: int
) -> None:
    """Both paths render a finished turn identically.

    They share one renderer precisely so an approval card cannot look different
    depending on which path produced it.
    """
    streamed = list(assistant.ask_streaming(messy, "tidy up this folder"))[-1]
    blocking = assistant.ask(messy, "tidy up this folder")
    assert streamed == blocking


def test_a_greeting_never_reaches_the_model(
    assistant: AssistantPanel, messy: int
) -> None:
    """Conversation is answered directly, in one frame and no model call."""
    frames = list(assistant.ask_streaming(messy, "hi"))
    assert len(frames) == 1
    assert "a-thinking" not in frames[0][0]
    assert "Hello" in frames[0][0]


def test_tidy_phrasing_uses_the_deterministic_service(
    assistant: AssistantPanel, messy: int
) -> None:
    """"Tidy up this folder" is a rule, so it is answered without the model.

    It must still arrive at an approval card: skipping the model does not mean
    skipping consent.
    """
    message, card = assistant.ask(messy, "tidy up this folder")
    assert card
    assert "move" in message.lower()


def test_a_compound_request_still_goes_to_the_planner(
    assistant: AssistantPanel, messy: int
) -> None:
    """The tidy shortcut matches whole input only.

    "tidy up and email it" contains an outward step, and must not be quietly
    turned into a plain tidy.
    """
    frames = list(assistant.ask_streaming(messy, "tidy up and email it to my supervisor"))
    assert "a-thinking" in frames[0][0]


def test_planner_diagnostics_are_never_shown(
    assistant: AssistantPanel, messy: int
) -> None:
    """A failed plan explains itself in the user's terms.

    "pass 1: no usable steps in the reply" is written for a log. It was reaching
    the screen, which is what prompted this.
    """
    message, _ = assistant.ask(messy, "sing me a song about databases")
    assert "pass 1" not in message
    assert "usable steps" not in message


def _with_scripted_plan(assistant: AssistantPanel, *replies: str) -> None:
    """Replace the model with a fixed reply.

    These tests are about what the interface says, not about what a model
    chooses, so the plan is scripted. It also means they pass on a machine with
    no model installed.
    """
    from artemis.core.providers import ModelTier, StubProvider
    from artemis.core.router import ModelRouter

    router = ModelRouter(store=assistant._gateway.store)
    router.register(
        StubProvider(
            name="stub", tier=ModelTier.LOCAL, model="s", replies=list(replies)
        )
    )
    assistant._gateway.planner.router = router


# -- saying something useful ---------------------------------------------------
#
# These exist because the app was technically working and still not
# communicating: a directory listing was executed and reported as "Done: 1 list
# dir", a request to delete returned a file listing with no mention that
# deleting is impossible, and a model that was not running produced "I could
# not turn that into steps", which blames the user's phrasing for a missing
# dependency.


def test_a_listing_reports_what_it_found(
    assistant: AssistantPanel, messy: int
) -> None:
    """A read that answers nothing has not answered.

    The listing was in the result the whole time; only the count was shown.
    """
    _with_scripted_plan(
        assistant, '{"steps":[{"operation":"list_dir","paths":["."]}]}'
    )
    message, _ = assistant.ask(messy, "what files do i have")
    assert "a.pdf" in message
    assert "list dir" not in message.lower()


def test_reading_a_file_shows_its_contents(
    assistant: AssistantPanel, messy: int, store
) -> None:
    root = _root(store, messy)
    (root / "note.txt").write_text("remember the milk", encoding="utf-8")
    _with_scripted_plan(
        assistant,
        '{"steps":[{"operation":"read_file","paths":["note.txt"]}]}',
    )
    message, _ = assistant.ask(messy, "read note.txt")
    assert "remember the milk" in message


def test_asking_to_delete_explains_that_it_cannot(
    assistant: AssistantPanel, messy: int
) -> None:
    """The boundary is real, so it is stated rather than worked around."""
    message, card = assistant.ask(messy, "delete everything")
    assert "cannot delete" in message.lower()
    assert not card


def test_deleting_a_named_thing_is_also_explained(
    assistant: AssistantPanel, messy: int
) -> None:
    """"Delete the old invoices" is as much a deletion request as the general one."""
    message, _ = assistant.ask(messy, "remove the old invoices")
    assert "cannot delete" in message.lower()


def test_an_unreachable_model_says_so(
    assistant: AssistantPanel, messy: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing dependency must not be reported as an unclear request.

    This is the message a user sees when Ollama is not running, which is a
    perfectly ordinary situation on a desktop.
    """
    from artemis.core.router import NoModelAvailable

    def unavailable(*args, **kwargs):
        raise NoModelAvailable("nothing is listening")

    monkeypatch.setattr(assistant._gateway.router, "complete", unavailable)
    monkeypatch.setattr(assistant._gateway.router, "stream", unavailable)

    message, _ = assistant.ask(messy, "put my spreadsheets somewhere sensible")
    assert "could not reach the model" in message.lower()
    assert "could not turn that into steps" not in message.lower()


def test_an_unreachable_model_does_not_stop_the_model_free_features(
    assistant: AssistantPanel, messy: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tidying and "what changed" are deterministic, so they still work."""
    from artemis.core.router import NoModelAvailable

    def unavailable(*args, **kwargs):
        raise NoModelAvailable("nothing is listening")

    monkeypatch.setattr(assistant._gateway.router, "complete", unavailable)
    monkeypatch.setattr(assistant._gateway.router, "stream", unavailable)

    message, card = assistant.ask(messy, "tidy up this folder")
    assert card
    assert "could not reach" not in message.lower()


def test_what_changed_is_answered_in_the_conversation(
    assistant: AssistantPanel, messy: int, indexer, store, monkeypatch
) -> None:
    """The question is answered where it was asked, not only in the sidebar."""
    assistant._resume.checkpoint(messy)
    root = _root(store, messy)
    (root / "brand-new.txt").write_text("x", encoding="utf-8")
    indexer.scan(messy)

    message, _ = assistant.ask(messy, "what changed recently")
    assert "brand-new.txt" in message


def test_an_approval_describes_the_plan_not_the_request(
    assistant: AssistantPanel, messy: int
) -> None:
    """Echoing the user's own words back tells them nothing.

    The question being asked is about consequences, so the consequences are
    what the message states.
    """
    message, card = assistant.ask(messy, "tidy up this folder")
    assert card
    assert "move" in message.lower()
