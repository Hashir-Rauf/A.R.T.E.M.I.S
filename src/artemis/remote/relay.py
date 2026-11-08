"""The edge: a relay that carries sealed frames and knows nothing else.

This is the stand-in for the cloud relay described in the architecture (a Worker with one
Durable Object per pairing). It does the same job and holds the same things: which rooms
exist, a one-way proof to let a device in, and frames it cannot read. It never holds a
code, a key, or any message in the clear. `seen` records every byte that passed through
it, so a test can prove the edge never saw plaintext.

Both ends connect out to it. This computer opens no inbound port.
"""

from __future__ import annotations

import hmac
import time
from collections import deque
from dataclasses import dataclass, field

MAX_PROOF_TRIES = 5


@dataclass
class _Room:
    proof: str
    expires: float
    tries: int = 0
    to_host: deque[bytes] = field(default_factory=deque)
    to_device: deque[bytes] = field(default_factory=deque)
    closed: bool = False


class Relay:
    def __init__(self, clock=time.time) -> None:
        self._rooms: dict[str, _Room] = {}
        self._clock = clock
        #: Everything the edge could ever read. A test inspects this.
        self.seen: list[bytes] = []

    def open_room(self, room_id: str, proof: str, ttl_seconds: float) -> None:
        self._rooms[room_id] = _Room(proof=proof, expires=self._clock() + ttl_seconds)

    def admit(self, room_id: str, proof: str) -> bool:
        """Let a device in if it holds the proof. A wrong guess counts; too many closes the room."""
        room = self._live(room_id)
        if room is None:
            return False
        if hmac.compare_digest(room.proof, proof):
            return True
        room.tries += 1
        if room.tries >= MAX_PROOF_TRIES:
            room.closed = True
        return False

    def send(self, room_id: str, from_host: bool, frame: bytes) -> bool:
        room = self._live(room_id)
        if room is None:
            return False
        self.seen.append(frame)
        (room.to_device if from_host else room.to_host).append(frame)
        return True

    def receive(self, room_id: str, as_host: bool) -> list[bytes]:
        room = self._live(room_id)
        if room is None:
            return []
        queue = room.to_host if as_host else room.to_device
        frames = list(queue)
        queue.clear()
        return frames

    def close(self, room_id: str) -> None:
        self._rooms.pop(room_id, None)

    def has_room(self, room_id: str) -> bool:
        return self._live(room_id) is not None

    def _live(self, room_id: str) -> _Room | None:
        room = self._rooms.get(room_id)
        if room is None or room.closed or room.expires < self._clock():
            return None
        return room
