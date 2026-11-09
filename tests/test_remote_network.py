"""Sprint 9: the same pairing and requests, over a real WebSocket relay on this computer."""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from pathlib import Path

import pytest

from artemis.core.indexer import Indexer
from artemis.core.providers import StubProvider
from artemis.core.workspace import WorkspaceManager
from artemis.data.store import Store
from artemis.remote.bridge import RemoteBridge
from artemis.remote.device import RemoteDevice
from artemis.remote.edge.server import run
from artemis.remote.netrelay import NetworkRelay
from artemis.remote.plane import RemotePlane
from artemis.ui.assistant import AssistantPanel

MOVE = (
    '{"steps":[{"operation":"move_file","paths":["a.pdf"],'
    '"arguments":{"destination":"Docs/a.pdf"}}]}'
)


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
    return fake


@pytest.fixture
def server_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    ready = threading.Event()

    def serve() -> None:
        async def main() -> None:
            flag = asyncio.Event()
            task = asyncio.ensure_future(run("127.0.0.1", port, flag))
            await flag.wait()
            ready.set()
            await task

        asyncio.run(main())

    threading.Thread(target=serve, daemon=True).start()
    assert ready.wait(10)
    return f"ws://127.0.0.1:{port}"


@pytest.fixture
def folder(manager: WorkspaceManager, indexer: Indexer, tmp_path: Path):
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.pdf").write_text("x", encoding="utf-8")
    ws = manager.grant(root, name="Work").id
    indexer.scan(ws)
    return ws, root


def test_pairing_and_a_request_work_over_a_real_relay(store: Store, folder, server_url) -> None:
    ws, root = folder
    host_relay = NetworkRelay(server_url)
    device_relay = NetworkRelay(server_url, wait=4)
    plane = RemotePlane(store, host_relay)

    def make_panel():
        panel = AssistantPanel(store)
        panel._router.providers = [StubProvider(replies=[MOVE])]
        return panel

    bridge = RemoteBridge(store, make_panel)
    plane.attach(bridge.handle)
    bridge.allow_workspace(ws, True)

    stop = threading.Event()

    def pump() -> None:
        while not stop.is_set():
            plane.pump_all()
            time.sleep(0.05)

    try:
        offer = plane.begin_pairing()
        device = RemoteDevice(device_relay, "Test phone")
        assert device.join(offer.pairing_id, offer.code)
        for _ in range(100):
            if plane.pending():
                break
            time.sleep(0.05)
        (waiting,) = plane.pending()
        assert waiting.safety_number == device.safety_number
        plane.confirm(waiting.pairing_id)
        assert device.finish_pairing()

        threading.Thread(target=pump, daemon=True).start()
        assert device.open_session(lambda: None)
        asked = device.request(lambda: None, op="ask", workspace_id=ws, text="put a.pdf in the Docs folder")
        assert asked["pending"] is True
        assert (root / "a.pdf").exists()
        device.request(lambda: None, op="approve")
        assert (root / "Docs" / "a.pdf").exists()
    finally:
        stop.set()
        host_relay.shutdown()
        device_relay.shutdown()


def test_a_wrong_code_is_refused_by_the_relay(store: Store, server_url) -> None:
    host_relay = NetworkRelay(server_url)
    plane = RemotePlane(store, host_relay)
    offer = plane.begin_pairing()
    device_relay = NetworkRelay(server_url, wait=1)
    try:
        assert RemoteDevice(device_relay).join(offer.pairing_id, "WRONGCODE1") is False
    finally:
        host_relay.shutdown()
        device_relay.shutdown()
