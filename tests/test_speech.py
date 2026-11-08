"""Sprint 8: speech is another way to type, and adds no gates of its own.

The stage gate for this sprint is that voice parity is structural. These tests pin the
three things that make it so: nothing is heard unless the session was armed, nothing is
kept, and a spoken request reaches exactly the same approval gate as a typed one.
Transcription and speaking are replaced by stand-ins, so no model or voice is needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.providers import StubProvider
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.services.speech import (
    MAX_SPOKEN_CHARS,
    NotArmed,
    SpeechUnavailable,
    VoiceSession,
)
from artemis.ui.assistant import AssistantPanel


class FakeEars:
    def __init__(self, words: str = "tidy up this folder") -> None:
        self.words = words
        self.heard: list[Path] = []

    def transcribe(self, audio_path: Path) -> str:
        assert audio_path.exists()
        self.heard.append(audio_path)
        return self.words


class FakeVoice:
    def __init__(self) -> None:
        self.said: list[str] = []

    def speak_to_file(self, text: str, out_path: Path) -> None:
        self.said.append(text)
        out_path.write_bytes(b"RIFF")


class BrokenEars:
    def transcribe(self, audio_path: Path) -> str:
        raise SpeechUnavailable("no model")


def _recording(tmp_path: Path) -> Path:
    p = tmp_path / "mic.wav"
    p.write_bytes(b"RIFFfake")
    return p


# -- never recorded unless armed ---------------------------------------------


def test_a_session_starts_disarmed_and_audio_is_refused_unread(tmp_path: Path) -> None:
    ears = FakeEars()
    session = VoiceSession(ears, FakeVoice())
    clip = _recording(tmp_path)

    assert session.armed is False
    with pytest.raises(NotArmed):
        session.hear(clip)

    assert ears.heard == []  # the audio was never read
    assert not clip.exists()  # and it was not kept either


def test_arming_then_disarming_stops_listening(tmp_path: Path) -> None:
    ears = FakeEars()
    session = VoiceSession(ears, FakeVoice())
    session.arm()
    assert session.hear(_recording(tmp_path)) is not None

    session.disarm()
    with pytest.raises(NotArmed):
        session.hear(_recording(tmp_path))


def test_the_recording_is_deleted_after_it_is_read(tmp_path: Path) -> None:
    session = VoiceSession(FakeEars("hello"), FakeVoice())
    session.arm()
    clip = _recording(tmp_path)

    turn = session.hear(clip)

    assert turn is not None and turn.text == "hello" and turn.spoken is True
    assert not clip.exists()


def test_the_recording_is_deleted_even_when_transcription_fails(tmp_path: Path) -> None:
    session = VoiceSession(BrokenEars(), FakeVoice())
    session.arm()
    clip = _recording(tmp_path)

    with pytest.raises(SpeechUnavailable):
        session.hear(clip)

    assert not clip.exists()


def test_silence_gives_no_turn(tmp_path: Path) -> None:
    session = VoiceSession(FakeEars("   "), FakeVoice())
    session.arm()
    assert session.hear(_recording(tmp_path)) is None
    assert session.hear(None) is None


def test_the_log_records_that_voice_was_used_but_never_what_was_said(
    store: Store, tmp_path: Path
) -> None:
    session = VoiceSession(FakeEars("my secret words"), FakeVoice(), audit=store.append_audit)
    session.arm()
    session.hear(_recording(tmp_path))
    session.disarm()

    rows = store.list_audit()
    events = [r["event"] for r in rows]
    assert {"voice.armed", "voice.heard", "voice.disarmed"} <= set(events)
    assert "my secret words" not in repr([dict(r) for r in rows])


# -- speaking back ------------------------------------------------------------


def test_a_reply_is_read_aloud_and_long_ones_are_shortened() -> None:
    voice = FakeVoice()
    session = VoiceSession(FakeEars(), voice)

    out = session.speak("It is done.")
    assert out is not None and out.exists()
    out.unlink()

    session.speak("word " * 500).unlink()
    assert len(voice.said[-1]) <= MAX_SPOKEN_CHARS + 40
    assert voice.said[-1].endswith("The rest is on the screen.")


def test_reading_aloud_can_be_turned_off() -> None:
    voice = FakeVoice()
    session = VoiceSession(FakeEars(), voice)
    session.set_read_aloud(False)

    assert session.speak("hello") is None
    assert voice.said == []


# -- the stage gate: a spoken request meets the same approval gate ------------


@pytest.fixture
def folder(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> tuple[int, Path]:
    root = tmp_path / "work"
    root.mkdir()
    for name in ("a.pdf", "b.pdf", "c.txt"):
        (root / name).write_text("x", encoding="utf-8")
    ws = manager.grant(root, name="Work").id
    indexer.scan(ws)
    return ws, root


REQUEST = "put a.pdf in the Docs folder"
PLAN = (
    '{"steps":[{"operation":"move_file","paths":["a.pdf"],'
    '"arguments":{"destination":"Docs/a.pdf"}}]}'
)


def test_a_spoken_change_waits_for_approval_exactly_like_a_typed_one(
    store: Store, folder, tmp_path: Path
) -> None:
    ws, root = folder
    before = sorted(p.name for p in root.iterdir())

    def fresh() -> AssistantPanel:
        panel = AssistantPanel(store)
        panel._router.providers = [StubProvider(replies=[PLAN])]
        return panel

    typed_message, typed_card = fresh().ask(ws, REQUEST)

    session = VoiceSession(FakeEars(REQUEST), FakeVoice())
    session.arm()
    turn = session.hear(_recording(tmp_path))
    spoken_panel = fresh()
    spoken_message, spoken_card = spoken_panel.ask(ws, turn.text)

    assert "Approve these changes?" in typed_card
    assert "Approve these changes?" in spoken_card  # same gate, no new one written
    assert spoken_panel.has_pending
    assert sorted(p.name for p in root.iterdir()) == before  # nothing happened yet
    assert typed_message == spoken_message


def test_a_spoken_email_is_never_sent_without_approval(store: Store, folder, tmp_path: Path) -> None:
    ws, _ = folder
    panel = AssistantPanel(store)
    panel._router.providers = [
        StubProvider(replies=["SUBJECT: Running late\nBODY:\nHi, I will be late.\nThanks"])
    ]
    session = VoiceSession(FakeEars("email sam@example.com to say I will be late"), FakeVoice())
    session.arm()
    turn = session.hear(_recording(tmp_path))

    _message, card = panel.ask(ws, turn.text)

    assert panel.has_pending  # waiting for a person, not sent
    assert "Approve" in card


# -- it should sound like a person, not read out the screen -------------------


def test_the_model_label_and_markup_are_never_spoken() -> None:
    from artemis.services.speech import spoken_form

    shown = "**Hello** there!\n- first thing\n- second thing\ngemma4:e4b \u00b7 on this computer"
    said = spoken_form(shown)

    assert "gemma" not in said and "on this computer" not in said
    assert "*" not in said and "- " not in said
    assert said.startswith("Hello there!")
    assert spoken_form("a \u00b7 b\ngemini-3.8-flash \u00b7 via gemini") == "a \u00b7 b."


def test_a_waiting_plan_is_spoken_as_an_invitation_to_look_not_read_out() -> None:
    from artemis.services.speech import spoken_form

    said = spoken_form("Approve these changes?\nMove a.pdf to Docs/a.pdf")

    assert "press Approve" in said and "a.pdf" not in said


def test_the_greeting_depends_on_the_time_of_day() -> None:
    from datetime import datetime

    from artemis.services.speech import greeting

    assert greeting(datetime(2026, 1, 1, 8)).startswith("Good morning")
    assert greeting(datetime(2026, 1, 1, 14)).startswith("Good afternoon")
    assert greeting(datetime(2026, 1, 1, 20)).startswith("Good evening")
    assert "ARTEMIS" in greeting()


def test_a_spoken_chat_is_worded_for_the_ear_and_never_names_the_model() -> None:
    from artemis.core.chat import ChatService

    typed = ChatService._prompt("hi", [], spoken=False)
    talked = ChatService._prompt("hi", [], spoken=True)

    assert "phone call" not in typed
    assert "phone call" in talked
    assert "Never say which model" in talked
