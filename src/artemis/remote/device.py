"""A reference remote device: what the phone's page does, written so it can be tested.

The real device is a web page. It does the same steps with the same maths, in the browser.
"""

from __future__ import annotations

import json
import secrets

from artemis.remote import crypto
from artemis.remote.relay import Relay


class RemoteDevice:
    def __init__(self, relay: Relay, name: str = "My phone") -> None:
        self._relay = relay
        self.name = name
        self.device_id: str | None = None
        self._key: bytes | None = None
        self._pair_key: bytes | None = None
        self._channel: crypto.Channel | None = None
        self.safety_number: str | None = None

    # -- pairing ---------------------------------------------------------------

    def join(self, pairing_id: str, code: str) -> bool:
        """Present the code. The edge learns only a one-way proof of it."""
        if not self._relay.admit(pairing_id, crypto.code_proof(code)):
            return False
        host_public = None
        for frame in self._relay.receive(pairing_id, as_host=False):
            if frame.startswith(b"HELLO"):
                host_public = frame[5:]
        if host_public is None:
            return False
        private, public = crypto.new_keypair()
        secret = crypto.shared_secret(private, host_public)
        self._pair_key = crypto.pairing_key(secret, code)
        self.safety_number = crypto.safety_number(secret, code)
        self._relay.send(pairing_id, False, b"JOIN" + public + self.name.encode())
        self._pairing_id = pairing_id
        return True

    def finish_pairing(self) -> bool:
        """Read the host's confirmation. Only arrives once the owner said yes."""
        if self._pair_key is None:
            return False
        channel = crypto.Channel(self._pair_key, b"D", b"H")
        for frame in self._relay.receive(self._pairing_id, as_host=False):
            try:
                reply = json.loads(channel.open(frame))
            except (crypto.CryptoError, ValueError):
                continue
            self.device_id = reply["device_id"]
            self._key = crypto.device_secret(self._pair_key)
            return True
        return False

    # -- sessions ---------------------------------------------------------------

    @property
    def _room(self) -> str:
        return f"dev:{self.device_id}"

    def _admit(self) -> bool:
        proof = crypto.derive(self._key, b"artemis-room-proof").hex()
        return self._relay.admit(self._room, proof)

    def open_session(self, host_pump) -> bool:
        """Sign in. `host_pump` lets the host answer; over a network it would be the wire."""
        if self._key is None or not self._admit():
            return False
        nonce = secrets.token_bytes(16)
        self._relay.send(self._room, False, b"S" + nonce)
        host_pump()
        for frame in self._relay.receive(self._room, as_host=False):
            if frame.startswith(b"S"):
                key = crypto.session_key(self._key, frame[1:], nonce)
                self._channel = crypto.Channel(key, b"D", b"H")
                return True
        return False

    def send(self, **payload) -> None:
        """A one-way request, such as a piece of audio. No answer is waited for."""
        if self._channel is None:
            raise RuntimeError("Not signed in.")
        self._relay.send(self._room, False, self._channel.seal(json.dumps(payload).encode()))

    def events(self) -> list[dict]:
        """Everything the host has sent since the last call (speech, replies, ...)."""
        found = []
        for frame in self._relay.receive(self._room, as_host=False):
            if self._channel is None:
                break
            try:
                found.append(json.loads(self._channel.open(frame)))
            except (crypto.CryptoError, ValueError):
                continue
        return found

    def request(self, host_pump, **payload) -> dict:
        if self._channel is None:
            raise RuntimeError("Not signed in.")
        self._relay.send(self._room, False, self._channel.seal(json.dumps(payload).encode()))
        host_pump()
        for frame in self._relay.receive(self._room, as_host=False):
            if frame == b"E":
                self._channel = None
                return {"error": "session_expired"}
            try:
                return json.loads(self._channel.open(frame))
            except (crypto.CryptoError, ValueError):
                continue
        return {"error": "no_answer"}
