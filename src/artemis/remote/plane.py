"""The host side of the remote plane: pairing, devices, sessions, revocation.

Nothing outside the `artemis.remote` package imports this. Delete the package and the rest
of ARTEMIS runs exactly as before; that is the stage gate, and a test enforces it.

Its tables are created here, not in the main schema, so removing the package also leaves
the main database untouched.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from artemis.data.store import Store
from artemis.remote import crypto
from artemis.remote.relay import Relay

_SCHEMA = """
CREATE TABLE IF NOT EXISTS remote_devices (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    secret     BLOB,                -- emptied the moment the device is revoked
    paired_at  TEXT NOT NULL,
    revoked_at TEXT
);
"""

PAIRING_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 3600

#: What a request is answered with. A request is a dict; so is the answer.
Handler = Callable[[str, dict], dict]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class PairingOffer:
    """What the host's screen shows: type the code, or scan it as a QR."""

    pairing_id: str
    code: str
    expires_in: int


@dataclass(frozen=True)
class PendingDevice:
    pairing_id: str
    name: str
    safety_number: str


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    paired_at: str
    revoked: bool


class _Pairing:
    def __init__(self, code: str, private, host_public: bytes) -> None:
        self.code = code
        self.private = private
        self.host_public = host_public
        self.device_name: str | None = None
        self.key: bytes | None = None
        self.safety: str | None = None


class _Session:
    def __init__(self, channel: crypto.Channel, expires: float) -> None:
        self.channel = channel
        self.expires = expires


class RemotePlane:
    def __init__(
        self,
        store: Store,
        relay: Relay,
        clock: Callable[[], float] = time.time,
        session_ttl: int = SESSION_TTL_SECONDS,
    ) -> None:
        self._store = store
        self._relay = relay
        self._clock = clock
        self._session_ttl = session_ttl
        self._pairings: dict[str, _Pairing] = {}
        self._sessions: dict[str, _Session] = {}
        self._handler: Handler | None = None

    def attach(self, handler: Handler) -> None:
        """The bridge that answers decoded requests. The plane never interprets them."""
        self._handler = handler

    def _ensure(self) -> None:
        with self._store._write() as conn:
            conn.executescript(_SCHEMA)

    # -- pairing ---------------------------------------------------------------

    def begin_pairing(self) -> PairingOffer:
        """Start pairing. The code is shown on this computer's screen only."""
        self._ensure()
        code = crypto.new_pairing_code()
        pairing_id = secrets.token_hex(8)
        private, public = crypto.new_keypair()
        self._pairings[pairing_id] = _Pairing(code, private, public)
        self._relay.open_room(pairing_id, crypto.code_proof(code), PAIRING_TTL_SECONDS)
        self._relay.send(pairing_id, True, b"HELLO" + public)
        self._store.append_audit("remote.pairing_started", "pending", detail={"pairing": pairing_id})
        return PairingOffer(pairing_id, code, PAIRING_TTL_SECONDS)

    def pending(self) -> list[PendingDevice]:
        """Devices that asked to pair and are waiting for the owner, here, to say yes."""
        for pairing_id, pairing in list(self._pairings.items()):
            if not self._relay.has_room(pairing_id):
                del self._pairings[pairing_id]  # expired or locked after wrong guesses
                continue
            if pairing.device_name is None:
                self._read_join(pairing_id, pairing)
        return [
            PendingDevice(pid, p.device_name, p.safety or "")
            for pid, p in self._pairings.items()
            if p.device_name is not None
        ]

    def _read_join(self, pairing_id: str, pairing: _Pairing) -> None:
        for frame in self._relay.receive(pairing_id, as_host=True):
            if not frame.startswith(b"JOIN") or len(frame) < 4 + 32:
                continue
            device_public = frame[4:36]
            name = frame[36:].decode("utf-8", "replace").strip()[:60] or "A device"
            secret = crypto.shared_secret(pairing.private, device_public)
            pairing.key = crypto.pairing_key(secret, pairing.code)
            pairing.safety = crypto.safety_number(secret, pairing.code)
            pairing.device_name = name
            return

    def confirm(self, pairing_id: str) -> Device:
        """The owner, at this computer, accepts the device. Without this nothing is paired."""
        self.pending()
        pairing = self._pairings.get(pairing_id)
        if pairing is None or pairing.device_name is None or pairing.key is None:
            raise LookupError("There is no device waiting to be confirmed.")
        device_id = secrets.token_hex(6)
        key = crypto.device_secret(pairing.key)
        with self._store._write() as conn:
            conn.execute(
                "INSERT INTO remote_devices (id, name, secret, paired_at) VALUES (?, ?, ?, ?)",
                (device_id, pairing.device_name, key, _now()),
            )
        channel = crypto.Channel(pairing.key, b"H", b"D")
        self._relay.send(
            pairing_id, True, channel.seal(json.dumps({"device_id": device_id}).encode())
        )
        self._open_device_room(device_id, key)
        self._store.append_audit(
            "remote.paired", "approved", detail={"device": device_id, "name": pairing.device_name}
        )
        del self._pairings[pairing_id]
        return Device(device_id, pairing.device_name, _now(), False)

    def reject(self, pairing_id: str) -> None:
        pairing = self._pairings.pop(pairing_id, None)
        self._relay.close(pairing_id)
        if pairing is not None:
            self._store.append_audit("remote.paired", "declined", detail={"pairing": pairing_id})

    # -- devices ---------------------------------------------------------------

    def devices(self) -> list[Device]:
        self._ensure()
        return [
            Device(r["id"], r["name"], r["paired_at"], r["revoked_at"] is not None)
            for r in self._store.query("SELECT * FROM remote_devices ORDER BY paired_at")
        ]

    def resume(self) -> None:
        """Reopen a meeting place for every device that is still paired (after a restart)."""
        self._ensure()
        for r in self._store.query(
            "SELECT id, secret FROM remote_devices WHERE revoked_at IS NULL"
        ):
            self._open_device_room(r["id"], bytes(r["secret"]))

    def revoke(self, device_id: str) -> None:
        """Instant, and decided here alone: the device cannot keep a session or open a new one."""
        self._ensure()
        with self._store._write() as conn:
            conn.execute(
                "UPDATE remote_devices SET revoked_at = ?, secret = NULL WHERE id = ?",
                (_now(), device_id),
            )
        self._sessions.pop(device_id, None)
        self._relay.close(f"dev:{device_id}")
        self._store.append_audit("remote.revoked", "done", detail={"device": device_id})

    def _open_device_room(self, device_id: str, key: bytes) -> None:
        proof = crypto.derive(key, b"artemis-room-proof").hex()
        self._relay.open_room(f"dev:{device_id}", proof, ttl_seconds=10**9)

    def _device_key(self, device_id: str) -> bytes | None:
        row = self._store.query_one(
            "SELECT secret FROM remote_devices WHERE id = ? AND revoked_at IS NULL", (device_id,)
        )
        return bytes(row["secret"]) if row and row["secret"] else None

    # -- sessions and requests --------------------------------------------------

    def pump(self, device_id: str) -> int:
        """Handle whatever this device has sent. Returns how many frames were handled."""
        self._ensure()
        key = self._device_key(device_id)
        room = f"dev:{device_id}"
        if key is None:
            return 0
        handled = 0
        for frame in self._relay.receive(room, as_host=True):
            handled += 1
            if frame.startswith(b"S"):
                self._start_session(device_id, key, room, frame[1:])
                continue
            session = self._sessions.get(device_id)
            if session is None or session.expires < self._clock():
                self._sessions.pop(device_id, None)
                self._relay.send(room, True, b"E")  # expired: sign in again
                self._store.append_audit("remote.session", "expired", detail={"device": device_id})
                continue
            try:
                request = json.loads(session.channel.open(frame))
            except (crypto.CryptoError, ValueError):
                continue
            answer = self._handler(device_id, request) if self._handler else {"error": "off"}
            self._relay.send(room, True, session.channel.seal(json.dumps(answer).encode()))
        return handled

    def _start_session(self, device_id: str, key: bytes, room: str, device_nonce: bytes) -> None:
        host_nonce = secrets.token_bytes(16)
        channel = crypto.Channel(
            crypto.session_key(key, host_nonce, device_nonce), b"H", b"D"
        )
        self._sessions[device_id] = _Session(channel, self._clock() + self._session_ttl)
        self._relay.send(room, True, b"S" + host_nonce)
        self._store.append_audit("remote.session", "started", detail={"device": device_id})

    def end_all_sessions(self) -> None:
        """For when this computer sleeps or ARTEMIS closes: no session outlives it."""
        self._sessions.clear()
