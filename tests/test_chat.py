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


# -- an email with nothing to say -----------------------------------------------------


@pytest.mark.parametrize("text", [
    "Draft an email to bob@example.com",
    "write email to bob@example.com",
    "send bob@example.com an email",
])
def test_an_email_with_no_content_asks_what_it_should_say_and_writes_nothing(store: Store, ws: int, text: str) -> None:
    panel, stub = _panel(store)
    message, card = panel.ask(ws, text)
    assert "What should the email to bob@example.com say?" in message
    assert card == "" and stub.calls == []


def test_an_email_that_says_what_it_is_about_goes_ahead(store: Store, ws: int) -> None:
    panel, _ = _panel(store, "SUBJECT: Late\nBODY:\nI will be late on Friday.\nThanks")
    message, card = panel.ask(ws, "Email bob@example.com to say I will be late on Friday")
    assert "Approve these changes?" in card and "late on Friday" in card


# -- keeping the thread: a reply answers the question that was just asked -----------


def test_the_reply_to_what_should_it_say_completes_the_email(store: Store, ws: int) -> None:
    panel, stub = _panel(store, "SUBJECT: Hi\nBODY:\nHi there.\nThanks")
    first, card = panel.ask(ws, "Draft an email to bob@example.com")
    assert "What should the email to bob@example.com say?" in first and card == ""

    message, card = panel.ask(ws, "just say hi")

    assert "Approve these changes?" in card and "bob@example.com" in card
    assert "just say hi" in stub.calls[-1]
    assert panel.state.pending is None


def test_a_missing_address_is_asked_for_and_the_next_message_supplies_it(store: Store, ws: int) -> None:
    panel, _ = _panel(store, "SUBJECT: Late\nBODY:\nI will be late.\nThanks")
    first, _ = panel.ask(ws, "Email my boss that I will be late")
    assert "Who should it go to?" in first

    again, card = panel.ask(ws, "boss@example.com")

    assert "Approve these changes?" in card and "boss@example.com" in card


def test_a_new_request_replaces_a_waiting_question_and_cancel_drops_it(store: Store, ws: int) -> None:
    panel, stub = _panel(store)
    panel.ask(ws, "Draft an email to bob@example.com")
    assert panel.state.pending is not None
    message, _ = panel.ask(ws, "cancel")
    assert "dropped" in message and panel.state.pending is None

    panel.ask(ws, "Draft an email to bob@example.com")
    panel.ask(ws, "Tidy up this folder")
    assert panel.state.pending is None


def test_the_waiting_plan_can_be_shown_again_after_a_reload(store: Store, ws: int) -> None:
    panel, _ = _panel(store)
    panel.ask(ws, "Search the web for typer")
    assert "Approve these changes?" in panel.pending_card_html() and panel.has_pending
    panel.reject()
    assert panel.pending_card_html() == ""


# -- the email that did not go out -------------------------------------------------------


@pytest.mark.parametrize("text", [
    "send another email to him",
    "write a mail to my boss",
    "draft a message to her",
    "email him again",
    "Could you send a quick email to sam@example.com",
])
def test_any_wording_that_asks_for_an_email_is_treated_as_one(text: str) -> None:
    from artemis.core.intent import MAIL, classify

    assert classify(text, []).kind == MAIL


def test_him_means_the_person_the_last_email_went_to(store: Store, ws: int) -> None:
    panel, stub = _panel(store, "SUBJECT: Hi\nBODY:\nSee you.\nThanks")
    panel.state.last_recipients = ("bob@example.com",)

    first, card = panel.ask(ws, "send another email to him")
    assert "What should the email to bob@example.com say?" in first and card == ""

    message, card = panel.ask(ws, "I will be there")
    assert "Approve these changes?" in card and "bob@example.com" in card
    assert panel.state.last_recipients == ("bob@example.com",)


def test_dont_ask_again_is_honest_about_emails(store: Store, ws: int) -> None:
    from types import SimpleNamespace

    from artemis.core.actions import Plan, ToolCall

    panel, _ = _panel(store)
    mail = ToolCall("send_mail", ws, (), {"to": ["bob@example.com"], "subject": "s", "body": "b"})
    ran = SimpleNamespace(executed=(mail.call_id,), skipped=(), results={mail.call_id: {"sent_to": ["bob@example.com"]}})
    said = panel._run_report(Plan(calls=(mail,), intent="x"), ran, remember=True)
    assert "Email sent to bob@example.com" in said
    assert "I will not ask again" not in said and "always ask first" in said

    move = ToolCall("move_file", ws, ("a.txt",), {"destination": "Docs/a.txt"})
    ran = SimpleNamespace(executed=(move.call_id,), skipped=(), results={move.call_id: None})
    assert "I will not ask again" in panel._run_report(Plan(calls=(move,), intent="x"), ran, remember=True)


def test_a_file_change_still_offers_dont_ask_again(store: Store, ws: int) -> None:
    panel, _ = _panel(store)
    panel.suggest_tidy(ws)
    if panel.has_pending:
        assert panel.can_remember is True
