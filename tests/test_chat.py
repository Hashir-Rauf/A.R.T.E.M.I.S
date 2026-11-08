"""Talking to ARTEMIS, and the small screens that used to be dead ends.

There was no chat at all: a message that was not a file task was forced through
the file planner or the file-grounded answerer. These tests drive the same
methods the page calls, with a scripted stand-in for the model.
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
    panel._router.providers = [stub]
    return panel, stub


@pytest.fixture
def ws(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> int:
    root = tmp_path / "work"
    root.mkdir()
    (root / "notes.md").write_text("Decided to use SQLite.\n", encoding="utf-8")
    workspace_id = manager.grant(root, name="Work").id
    indexer.scan(workspace_id)
    return workspace_id


# -- conversation ------------------------------------------------------------------


def test_chat_works_with_no_folder_at_all(store: Store) -> None:
    panel, stub = _panel(store, "Hi! What are you working on?")

    message, card = panel.ask(None, "hello")

    assert "What are you working on?" in message and card == ""
    assert len(stub.calls) == 1


def test_a_reply_says_which_model_answered_and_where(store: Store) -> None:
    panel, _ = _panel(store, "Fine, thanks.")

    message, _ = panel.ask(None, "how are you?")

    assert "stub" in message and "on this computer" in message


def test_the_conversation_is_remembered_for_the_next_message(store: Store) -> None:
    panel, stub = _panel(store, "Paris.", "About two million people.")

    first, _ = panel.ask(None, "What is the capital of France?")
    panel.log_turn("What is the capital of France?", first)
    panel.ask(None, "And how many people live there?")

    assert "capital of France" in stub.calls[1] and "Paris." in stub.calls[1]


def test_the_transcript_keeps_turns_in_order_and_can_be_cleared(store: Store) -> None:
    panel, _ = _panel(store)
    panel.log_turn("first", '<div class="a-msg">one</div>')
    html = panel.log_turn("second", '<div class="a-msg">two</div>')

    assert html.index("second") < html.index("first")  # newest first; the page reverses it
    assert panel.clear_chat() == "" and panel.transcript_html() == ""


def test_something_that_needs_a_folder_says_so_instead_of_chatting(store: Store) -> None:
    panel, stub = _panel(store)

    message, card = panel.ask(None, "Tidy up this folder")

    assert "folder" in message and card == "" and stub.calls == []


def test_a_message_about_a_file_is_a_file_task_not_chat(store: Store, ws: int) -> None:
    panel, stub = _panel(store, '{"steps":[{"operation":"read_file","paths":["notes.md"]}]}')

    message, _ = panel.ask(ws, "read notes.md")

    assert "SQLite" in message  # the file's own text, not a chat reply
    assert "on this computer" not in message


def test_asking_what_it_can_do_lists_examples_without_calling_the_model(store: Store) -> None:
    panel, stub = _panel(store)

    message, _ = panel.ask(None, "what can you do?")

    assert "Draft a document" in message and "Search the web" in message
    assert stub.calls == []


# -- notes, habits and remembered choices -------------------------------------------


def test_a_note_left_for_next_time_comes_back(store: Store, ws: int) -> None:
    panel, _ = _panel(store)

    saved = panel.save_note(ws, "Finish the survey analysis first")

    assert "Saved" in saved
    assert "Finish the survey analysis first" in panel.resume_html(ws)


def test_a_noticed_habit_can_be_accepted_or_declined(store: Store, ws: int) -> None:
    panel, _ = _panel(store)
    first = store.propose_rule(ws, "move_file::txt | moving TXT files")
    second = store.propose_rule(ws, "create_dir:: | creating a folder for files")

    assert sorted(label for label, _ in panel.habit_choices(ws)) == [
        "creating a folder for files", "moving TXT files",
    ]
    assert "Saved" in panel.decide_habit(ws, first, accept=True)
    assert "not bring this up again" in panel.decide_habit(ws, second, accept=False)
    assert panel.habit_choices(ws) == []
    assert panel.accepted_habits(ws) == ["moving TXT files"]


def test_a_dont_ask_again_choice_can_be_seen_and_taken_back(
    store: Store, ws: int, tmp_path: Path
) -> None:
    from artemis.core.actions import ToolCall

    panel, _ = _panel(store)
    panel._gateway.policy.remember(ToolCall("move_file", ws, ("a.txt",)))

    listed = panel.remembered_rules(ws)
    assert [label for label, _ in listed] == ["Do not ask before moving files"]

    assert "ask before doing that again" in panel.revoke_rule(listed[0][1])
    assert panel.remembered_rules(ws) == []


# -- streaming ----------------------------------------------------------------------


def test_a_chat_reply_arrives_in_pieces_and_the_last_frame_is_the_whole_answer(store: Store) -> None:
    panel, _ = _panel(store, "Hello there, friend.")

    frames = list(panel.ask_streaming(None, "hello"))

    assert "a-thinking" in frames[0][0]
    partials = [f for f, _ in frames if "a-streaming" in f]
    final = frames[-1][0]
    assert partials, "text should be shown while it is still arriving"
    assert "a-streaming" not in final and "Hello there, friend." in final
    assert "stub" in final


def test_bold_and_bullets_are_shown_as_formatting_and_nothing_else_becomes_markup() -> None:
    from artemis.ui.assistant import _rich

    out = _rich("**Hi** <script>x</script>\n- one\n- `code`")
    assert "<strong>Hi</strong>" in out and "\u2022 one" in out and "<code>code</code>" in out
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_a_cloud_reply_is_read_as_it_streams(monkeypatch) -> None:
    import io

    from artemis.core.providers import OpenAICompatibleProvider

    body = (
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        b"data: [DONE]\n\n"
    )

    class _R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *e):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: _R(body))
    provider = OpenAICompatibleProvider(name="x", api_key="k")
    assert list(provider.stream("hi")) == ["Hel", "lo"]


# -- saved chats ---------------------------------------------------------------------


def test_a_conversation_is_saved_and_can_be_reopened_later(store: Store) -> None:
    panel, _ = _panel(store)
    panel.log_turn("hello", '<div class="a-msg">Hi!</div>')
    panel.log_turn("and again", '<div class="a-msg">Hello again</div>')

    labels = [label for label, _ in panel.chat_choices()]
    assert len(labels) == 1 and labels[0].startswith("hello") and "today" in labels[0]

    other = AssistantPanel(store)  # a fresh start, as after restarting the app
    sid = other.chat_choices()[0][1]
    html = other.open_chat(sid)
    assert "Hi!" in html and "Hello again" in html and "and again" in html


def test_a_new_chat_does_not_overwrite_the_old_one(store: Store) -> None:
    panel, _ = _panel(store)
    panel.log_turn("first topic", "<div>a</div>")
    panel.new_chat()
    panel.log_turn("second topic", "<div>b</div>")
    assert [l.split("  ")[0] for l, _ in panel.chat_choices()] == ["second topic", "first topic"]


def test_a_chat_not_used_for_a_week_is_dropped_and_a_recent_one_stays(store: Store) -> None:
    old = store.create_chat("old chat")
    new = store.create_chat("recent chat")
    with store._write() as conn:
        conn.execute("UPDATE chat_sessions SET updated_at = '2020-01-01T00:00:00+00:00' WHERE id = ?", (old,))
    ids = [row["id"] for row in store.list_chats()]
    assert ids == [new]


def test_deleting_a_chat_removes_it_and_its_messages(store: Store) -> None:
    panel, _ = _panel(store)
    panel.log_turn("secret plans", "<div>x</div>")
    sid = panel.state.session_id
    panel.delete_chat()
    assert panel.chat_choices() == [] and store.chat_turns(sid) == []


def test_the_chat_list_is_stored_on_this_computer_only_in_the_artemis_database(store: Store) -> None:
    store.create_chat("x")
    assert store.query_one("SELECT COUNT(*) c FROM chat_sessions")["c"] == 1
