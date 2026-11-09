"""Sprint 9: real-time voice from a paired device, under the same rules as typing."""

from __future__ import annotations

import base64
import struct
from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.providers import StubProvider
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.remote.bridge import RemoteBridge
from artemis.remote.device import RemoteDevice
from artemis.remote.plane import RemotePlane
from artemis.remote.relay import Relay
from artemis.services.speech import VoiceSession
from artemis.ui.assistant import AssistantPanel

MOVE = (
    '{"steps":[{"operation":"move_file","paths":["a.pdf"],'
    '"arguments":{"destination":"Docs/a.pdf"}}]}'
)


def tone(seconds: float = 0.2) -> bytes:
    n = int(16000 * seconds)
    return struct.pack("<" + "h" * n, *([9000, -9000] * (n // 2)))


def quiet(seconds: float = 0.2) -> bytes:
    return bytes(int(16000 * seconds) * 2)


class FakeEars:
    def __init__(self, words: str) -> None:
        self.words = words
        self.heard = 0

    def transcribe(self, path):  # never used: audio from a device is not a file
        raise AssertionError("audio from a device must never be a file")

    def transcribe_pcm(self, pcm: bytes) -> str:
        self.heard += 1
        return self.words


class FakeVoice:
    def speak_to_file(self, text: str, out_path: Path) -> None:
        out_path.write_bytes(b"RIFFwav:" + text.encode())


class FakeKeyring:
    def __init__(self) -> None:
        self.items: dict = {}

    def set_password(self, service, name, value):
        self.items[(service, name)] = value

    def get_password(self, service, name):
        return self.items.get((service, name))

    def delete_password(self, service, name):
        self.items.pop((service, name), None)


@pytest.fixture(autouse=True)
def keyring(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr("artemis.data.credentials._keyring", lambda: fake)


@pytest.fixture
def folder(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path):
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.pdf").write_text("x", encoding="utf-8")
    ws = manager.grant(root, name="Work").id
    indexer.scan(ws)
    return ws, root


class World:
    def __init__(self, store: Store, ws: int, words: str, replies: list[str]) -> None:
        self.relay = Relay()
        self.plane = RemotePlane(store, self.relay)
        self.ears = FakeEars(words)
        self.store = store

        def panel():
            p = AssistantPanel(store)
            p._router.providers = [StubProvider(replies=list(replies))]
            return p

        self.bridge = RemoteBridge(
            store, panel, lambda: VoiceSession(self.ears, FakeVoice(), audit=store.append_audit)
        )
        self.plane.attach(self.bridge.handle)
        self.bridge.allow_workspace(ws, True)
        self.ws = ws
        offer = self.plane.begin_pairing()
        self.device = RemoteDevice(self.relay, "Phone")
        self.device.join(offer.pairing_id, offer.code)
        (waiting,) = self.plane.pending()
        self.plane.confirm(waiting.pairing_id)
        self.device.finish_pairing()
        self.pump = lambda: self.plane.pump(self.device.device_id)
        assert self.device.open_session(self.pump)

    def say(self, **payload) -> list[dict]:
        self.device.send(**payload)
        self.pump()
        return self.device.events()

    def audio(self, pcm: bytes) -> list[dict]:
        return self.say(op="voice_chunk", pcm=base64.b64encode(pcm).decode())

    def start(self) -> list[dict]:
        return self.say(op="voice_start", workspace_id=self.ws)

    def ready(self) -> None:
        """Voice allowed, started, greeting played, listening."""
        self.bridge.set_voice_allowed(True)
        self.start()
        self.say(op="voice_resume")

    def speak_then_pause(self, speaking: float = 1.0, pause: float = 4.0) -> list[dict]:
        events: list[dict] = []
        for _ in range(int(speaking / 0.2)):
            events += self.audio(tone())
        for _ in range(int(pause / 0.2)):
            events += self.audio(quiet())
        return events


def types(events: list[dict]) -> list[str]:
    return [e["type"] for e in events]


def test_voice_is_refused_until_the_owner_allows_it(store: Store, folder) -> None:
    world = World(store, folder[0], "hello", ["Hi there."])

    assert world.start()[0]["type"] == "error"
    assert world.audio(tone()) == []  # audio with no started session is dropped unread
    assert world.ears.heard == 0

    world.bridge.set_voice_allowed(True)
    assert "speech" in types(world.start())


def test_starting_voice_greets_with_text_and_sound(store: Store, folder) -> None:
    world = World(store, folder[0], "hello", ["Hi."])
    world.bridge.set_voice_allowed(True)

    events = world.start()

    assert events[0]["type"] == "speech" and "ARTEMIS" in events[0]["text"]
    assert base64.b64decode(events[0]["wav"]).startswith(b"RIFF")
    assert types(events)[-1] == "listening"


def test_silence_makes_it_speak_first_once_then_it_keeps_listening(store: Store, folder) -> None:
    world = World(store, folder[0], "hello", ["Hi."])
    world.ready()

    first: list[dict] = []
    for _ in range(25):  # five seconds of nothing
        first += world.audio(quiet())
    said = [e["text"] for e in first if e["type"] == "speech"]
    assert said == ["Hello? Is there anything I can help you with?"]

    world.say(op="voice_resume")
    later: list[dict] = []
    for _ in range(100):  # twenty more seconds of nothing
        later += world.audio(quiet())
    assert later == []  # it does not nag


def test_a_spoken_question_is_answered_in_text_and_sound_together(store: Store, folder) -> None:
    world = World(store, folder[0], "tell me about space", ["Space is big. It is also very cold. Want more?"])
    world.ready()

    events = world.speak_then_pause()

    kinds = types(events)
    assert kinds[:2] == ["thinking", "heard"]
    assert events[1]["text"] == "tell me about space"
    said = [e["text"] for e in events if e["type"] == "speech"]
    assert said and " ".join(said).startswith("Space is big.")
    assert all(base64.b64decode(e["wav"]).startswith(b"RIFF") for e in events if e["type"] == "speech")
    assert kinds[-2:] == ["reply", "done"]
    assert world.ears.heard == 1


def test_a_spoken_change_still_waits_for_approval(store: Store, folder) -> None:
    ws, root = folder
    world = World(store, ws, "put a.pdf in the Docs folder", [MOVE])
    world.ready()

    events = world.speak_then_pause()

    reply = next(e for e in events if e["type"] == "reply")
    assert reply["pending"] is True
    assert (root / "a.pdf").exists() and not (root / "Docs").exists()
    spoken = " ".join(e["text"] for e in events if e["type"] == "speech")
    assert "press Approve" in spoken and "a.pdf" not in spoken  # it says to look, not the details


def test_the_edge_never_sees_what_was_said_or_heard(store: Store, folder) -> None:
    world = World(store, folder[0], "my secret plan", ["The answer is forty two."])
    world.ready()
    world.speak_then_pause()

    seen = b"".join(world.relay.seen)
    assert b"my secret plan" not in seen and b"forty two" not in seen
    assert base64.b64encode(b"RIFF") not in seen


def test_the_log_records_voice_use_but_never_the_words(store: Store, folder) -> None:
    world = World(store, folder[0], "my secret plan", ["The answer is forty two."])
    world.ready()
    world.speak_then_pause()

    rows = [dict(r) for r in store.list_audit(100)]
    events = {r["event"] for r in rows}
    assert {"remote.voice_start", "voice.armed", "voice.heard"} <= events
    assert "my secret plan" not in repr(rows) and "forty two" not in repr(rows)
    assert store.verify_audit_chain()


def test_switching_voice_off_stops_it_at_once(store: Store, folder) -> None:
    world = World(store, folder[0], "hello", ["Hi."])
    world.ready()

    world.bridge.set_voice_allowed(False)

    assert world.speak_then_pause() == []
    assert world.ears.heard == 0


def test_stopping_voice_disarms_it(store: Store, folder) -> None:
    world = World(store, folder[0], "hello", ["Hi."])
    world.ready()

    assert world.say(op="voice_stop")[-1]["type"] == "stopped"
    assert world.audio(tone()) == []
    assert world.ears.heard == 0
