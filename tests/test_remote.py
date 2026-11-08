"""Sprint 9: the remote plane is optional, unreadable to the edge, and never above local.

The relay is the in-memory stand-in for the cloud edge, so these tests need no network.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.providers import StubProvider
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.remote import crypto
from artemis.remote.bridge import RemoteBridge
from artemis.remote.device import RemoteDevice
from artemis.remote.plane import RemotePlane
from artemis.remote.relay import Relay
from artemis.ui.assistant import AssistantPanel

SRC = Path(__file__).resolve().parents[1] / "src" / "artemis"
MOVE = (
    '{"steps":[{"operation":"move_file","paths":["a.pdf"],'
    '"arguments":{"destination":"Docs/a.pdf"}}]}'
)
EMAIL = "SUBJECT: Running late\nBODY:\nHi, I will be late.\nThanks"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def folder(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path) -> tuple[int, Path]:
    root = tmp_path / "work"
    root.mkdir()
    for name in ("a.pdf", "b.pdf"):
        (root / name).write_text("x", encoding="utf-8")
    ws = manager.grant(root, name="Work").id
    indexer.scan(ws)
    return ws, root


def _world(store: Store, replies: list[str] | None = None, clock: Clock | None = None):
    relay = Relay(clock=clock or Clock())
    plane = RemotePlane(store, relay, clock=clock or Clock())
    if clock is not None:
        plane = RemotePlane(store, relay, clock=clock, session_ttl=60)

    def make_panel() -> AssistantPanel:
        panel = AssistantPanel(store)
        panel._router.providers = [StubProvider(replies=list(replies or [MOVE]))]
        return panel

    bridge = RemoteBridge(store, make_panel)
    plane.attach(bridge.handle)
    return relay, plane, bridge


def _pair(plane: RemotePlane, relay: Relay, name: str = "My phone") -> RemoteDevice:
    offer = plane.begin_pairing()
    device = RemoteDevice(relay, name)
    assert device.join(offer.pairing_id, offer.code)
    (waiting,) = plane.pending()
    assert waiting.safety_number == device.safety_number  # both screens agree
    plane.confirm(waiting.pairing_id)
    assert device.finish_pairing()
    return device


# -- pairing --------------------------------------------------------------------


def test_a_device_is_not_paired_until_the_owner_confirms_on_the_computer(store: Store) -> None:
    relay, plane, _ = _world(store)
    offer = plane.begin_pairing()
    device = RemoteDevice(relay)
    assert device.join(offer.pairing_id, offer.code)

    assert len(plane.pending()) == 1
    assert plane.devices() == []  # the code alone paired nothing
    assert device.finish_pairing() is False  # and the device has no way in yet

    plane.confirm(offer.pairing_id)
    assert device.finish_pairing() is True
    assert [d.name for d in plane.devices()] == ["My phone"]


def test_a_declined_device_never_gets_in(store: Store) -> None:
    relay, plane, _ = _world(store)
    offer = plane.begin_pairing()
    device = RemoteDevice(relay)
    device.join(offer.pairing_id, offer.code)
    plane.pending()
    plane.reject(offer.pairing_id)

    assert plane.devices() == []
    assert device.finish_pairing() is False


def test_a_wrong_code_is_refused_and_guessing_locks_the_pairing(store: Store) -> None:
    relay, plane, _ = _world(store)
    offer = plane.begin_pairing()
    for _ in range(5):
        assert RemoteDevice(relay).join(offer.pairing_id, "WRONGCODE1") is False

    assert RemoteDevice(relay).join(offer.pairing_id, offer.code) is False  # too many guesses
    assert plane.pending() == []


def test_the_code_is_part_of_the_key_so_an_edge_that_swaps_keys_gains_nothing() -> None:
    mine, my_public = crypto.new_keypair()
    theirs, their_public = crypto.new_keypair()
    secret = crypto.shared_secret(mine, their_public)

    assert crypto.pairing_key(secret, "ABCDEFGHJK") != crypto.pairing_key(secret, "ZZZZZZZZZZ")
    assert crypto.safety_number(secret, "ABCDEFGHJK") != crypto.safety_number(secret, "ZZZZZZZZZZ")
    assert crypto.code_proof("ABCDEFGHJK") != "ABCDEFGHJK"  # what the edge sees is not the code


# -- the edge cannot read anything ---------------------------------------------------


def test_the_edge_never_sees_a_message_in_the_clear(store: Store, folder) -> None:
    ws, _ = folder
    relay, plane, bridge = _world(store)
    bridge.allow_workspace(ws, True)
    device = _pair(plane, relay)
    assert device.open_session(lambda: plane.pump(device.device_id))

    secret_words = "please move a.pdf into Docs, my secret plan"
    answer = device.request(lambda: plane.pump(device.device_id), op="ask", workspace_id=ws, text=secret_words)

    assert "Approve" in answer["card"] or answer["pending"]
    everything_the_edge_saw = b"".join(relay.seen)
    assert secret_words.encode() not in everything_the_edge_saw
    assert b"a.pdf" not in everything_the_edge_saw
    assert b"Approve" not in everything_the_edge_saw
    assert bridge  # keeps the reference alive


def test_a_replayed_frame_is_not_answered_twice(store: Store, folder) -> None:
    ws, _ = folder
    relay, plane, bridge = _world(store)
    bridge.allow_workspace(ws, True)
    device = _pair(plane, relay)
    device.open_session(lambda: plane.pump(device.device_id))
    device.request(lambda: plane.pump(device.device_id), op="workspaces")

    last_request = relay.seen[-2]  # the sealed request, copied by someone on the edge
    relay.send(f"dev:{device.device_id}", False, last_request)
    audit_before = store.count_audit()
    plane.pump(device.device_id)

    assert store.count_audit() == audit_before  # nothing was done a second time


# -- never more than local -----------------------------------------------------------


def test_a_folder_is_hidden_from_remote_until_the_owner_allows_it(store: Store, folder) -> None:
    ws, root = folder
    relay, plane, bridge = _world(store)
    device = _pair(plane, relay)
    device.open_session(lambda: plane.pump(device.device_id))
    pump = lambda: plane.pump(device.device_id)  # noqa: E731

    assert device.request(pump, op="workspaces")["workspaces"] == []
    refused = device.request(pump, op="ask", workspace_id=ws, text="put a.pdf in the Docs folder")
    assert "error" in refused
    assert sorted(p.name for p in root.iterdir()) == ["a.pdf", "b.pdf"]

    bridge.allow_workspace(ws, True)
    assert [w["id"] for w in device.request(pump, op="workspaces")["workspaces"]] == [ws]
    bridge.allow_workspace(ws, False)  # and the owner can take it back at once
    assert "error" in device.request(pump, op="ask", workspace_id=ws, text="hello")


def test_a_change_asked_for_remotely_still_waits_for_approval(store: Store, folder) -> None:
    ws, root = folder
    relay, plane, bridge = _world(store)
    bridge.allow_workspace(ws, True)
    device = _pair(plane, relay)
    device.open_session(lambda: plane.pump(device.device_id))
    pump = lambda: plane.pump(device.device_id)  # noqa: E731

    asked = device.request(pump, op="ask", workspace_id=ws, text="put a.pdf in the Docs folder")
    assert asked["pending"] is True
    assert (root / "a.pdf").exists() and not (root / "Docs").exists()  # nothing yet

    device.request(pump, op="approve")
    assert (root / "Docs" / "a.pdf").exists()


def test_an_email_cannot_be_approved_from_a_remote_device(store: Store, folder) -> None:
    ws, _ = folder
    relay, plane, bridge = _world(store, replies=[EMAIL])
    bridge.allow_workspace(ws, True)
    device = _pair(plane, relay)
    device.open_session(lambda: plane.pump(device.device_id))
    pump = lambda: plane.pump(device.device_id)  # noqa: E731

    asked = device.request(pump, op="ask", workspace_id=ws, text="email sam@example.com to say I will be late")
    assert asked["pending"] and asked["leaves_computer"]

    answer = device.request(pump, op="approve")

    assert answer.get("waiting_on_computer") is True
    panel = bridge._panels[device.device_id]
    assert panel.has_pending  # still waiting, for the computer


def test_a_remote_device_can_do_nothing_but_ask_and_answer(store: Store, folder) -> None:
    relay, plane, _ = _world(store)
    device = _pair(plane, relay)
    device.open_session(lambda: plane.pump(device.device_id))
    pump = lambda: plane.pump(device.device_id)  # noqa: E731

    for op in ("settings", "forget_key", "add_folder", "erase", "set_model", ""):
        assert "error" in device.request(pump, op=op)


def test_every_remote_request_is_logged_with_its_device(store: Store, folder) -> None:
    ws, _ = folder
    relay, plane, bridge = _world(store)
    bridge.allow_workspace(ws, True)
    device = _pair(plane, relay, name="Hashir's phone")
    device.open_session(lambda: plane.pump(device.device_id))
    device.request(lambda: plane.pump(device.device_id), op="ask", workspace_id=ws, text="hello there")

    rows = [r for r in store.list_audit(50) if r["event"].startswith("remote.")]
    events = {r["event"] for r in rows}
    assert {"remote.paired", "remote.session", "remote.ask"} <= events
    assert all(device.device_id in r["detail"] for r in rows if r["event"] in ("remote.ask", "remote.paired"))
    assert store.verify_audit_chain()


# -- sessions and revocation ---------------------------------------------------------


def test_a_session_ends_on_its_own_and_must_be_opened_again(store: Store) -> None:
    clock = Clock()
    relay, plane, _ = _world(store, clock=clock)
    device = _pair(plane, relay)
    pump = lambda: plane.pump(device.device_id)  # noqa: E731
    assert device.open_session(pump)
    assert "workspaces" in device.request(pump, op="workspaces")

    clock.now += 61  # past the session's time limit
    assert device.request(pump, op="workspaces") == {"error": "session_expired"}

    assert device.open_session(pump)  # signing in again works
    assert "workspaces" in device.request(pump, op="workspaces")


def test_closing_the_app_ends_every_session(store: Store) -> None:
    relay, plane, _ = _world(store)
    device = _pair(plane, relay)
    pump = lambda: plane.pump(device.device_id)  # noqa: E731
    device.open_session(pump)

    plane.end_all_sessions()

    assert device.request(pump, op="workspaces") == {"error": "session_expired"}


def test_revoking_a_device_cuts_it_off_at_once_and_for_good(store: Store) -> None:
    relay, plane, _ = _world(store)
    device = _pair(plane, relay)
    pump = lambda: plane.pump(device.device_id)  # noqa: E731
    assert device.open_session(pump)

    plane.revoke(device.device_id)

    assert device.request(pump, op="workspaces").get("error") in ("no_answer", "session_expired")
    assert device.open_session(pump) is False
    assert plane.devices()[0].revoked is True


def test_a_paired_device_survives_a_restart_of_the_host(store: Store) -> None:
    relay, plane, bridge = _world(store)
    device = _pair(plane, relay)

    relay2 = Relay()
    plane2 = RemotePlane(store, relay2)
    plane2.attach(bridge.handle)
    plane2.resume()
    device._relay = relay2  # the phone reconnects to the same edge address

    assert device.open_session(lambda: plane2.pump(device.device_id))


# -- the stage gate: removing it changes nothing locally -----------------------------


def test_nothing_in_the_core_imports_the_remote_plane() -> None:
    offenders = []
    for path in SRC.rglob("*.py"):
        if "remote" in path.relative_to(SRC).parts[:1]:
            continue
        text = path.read_text(encoding="utf-8")
        if "artemis.remote" in text or "from artemis import remote" in text:
            # The one allowed mention is the optional Settings section, which sits in a try.
            guarded = path.name == "web.py" and "build_remote_section = None" in text
            if not guarded:
                offenders.append(str(path.relative_to(SRC)))
    assert offenders == []


def test_the_main_database_has_no_remote_tables() -> None:
    from artemis.data import store as store_module

    assert "remote" not in store_module._SCHEMA.lower()


def test_artemis_runs_with_the_remote_package_deleted(tmp_path: Path) -> None:
    """Block the package from importing, then use ARTEMIS as normal."""
    code = (
        "import sys; sys.modules['artemis.remote'] = None\n"
        "from artemis.data.store import Store\n"
        "from artemis.core.workspace import WorkspaceManager\n"
        "from artemis.ui.assistant import AssistantPanel\n"
        "import artemis.ui.web as web\n"
        "s = Store(); w = WorkspaceManager(s)\n"
        "assert web.build(s) is not None\n"
        "p = AssistantPanel(s); assert p is not None\n"
        "print('fine')\n"
    )
    home = tmp_path / "home"
    home.mkdir()
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=120,
        env={**__import__("os").environ, "ARTEMIS_HOME": str(home), "PYTHONPATH": str(SRC.parent)},
    )
    assert result.returncode == 0, result.stderr
    assert "fine" in result.stdout


def test_the_settings_page_builds_with_the_remote_section_present(store: Store) -> None:
    from artemis.ui.web import build

    assert build(store) is not None
