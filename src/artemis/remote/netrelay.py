"""The same Relay interface as relay.py, but over a real WebSocket to a relay server.

The host uses it to listen for devices, and a test (or any Python client) uses it as a device.
It connects OUT only. Frames that arrive are held in a local queue until `receive` collects them,
so the plane and the reference device work unchanged over the network.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from urllib.parse import quote

from websockets.asyncio.client import connect


class NetworkRelay:
    def __init__(self, base_url: str, wait: float = 0.0) -> None:
        """`base_url` like ws://127.0.0.1:8765. `wait` is how long a receive may wait for frames."""
        self._base = base_url.rstrip("/")
        self._wait = wait
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._conns: dict[tuple[str, bool], object] = {}
        self._queues: dict[tuple[str, bool], deque[bytes]] = {}
        self._deadline: dict[str, float] = {}

    def _run(self, coro, timeout: float = 10):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    async def _open(self, room_id: str, host: bool, proof: str, ttl: float):
        url = f"{self._base}/room/{quote(room_id)}?role={'host' if host else 'device'}&proof={proof}&ttl={int(ttl)}"
        ws = await connect(url, open_timeout=5)
        await asyncio.sleep(0.2)  # a refused proof closes the socket just after it opens
        if ws.close_code is not None:
            raise ConnectionRefusedError("The relay refused the proof.")
        queue = self._queues.setdefault((room_id, host), deque())

        async def reader() -> None:
            try:
                async for frame in ws:
                    queue.append(frame if isinstance(frame, bytes) else frame.encode())
            except Exception:
                pass

        asyncio.ensure_future(reader())
        self._conns[(room_id, host)] = ws

    # -- the Relay interface -----------------------------------------------------

    def open_room(self, room_id: str, proof: str, ttl_seconds: float) -> None:
        self._deadline[room_id] = time.time() + ttl_seconds
        self._run(self._open(room_id, True, proof, ttl_seconds))

    def admit(self, room_id: str, proof: str) -> bool:
        try:
            self._run(self._open(room_id, False, proof, 0))
            return True
        except Exception:
            return False

    def send(self, room_id: str, from_host: bool, frame: bytes) -> bool:
        ws = self._conns.get((room_id, from_host))
        if ws is None:
            return False
        try:
            self._run(ws.send(frame))
            return True
        except Exception:
            return False

    def receive(self, room_id: str, as_host: bool) -> list[bytes]:
        queue = self._queues.setdefault((room_id, as_host), deque())
        end = time.time() + self._wait
        while not queue and time.time() < end:
            time.sleep(0.03)
        frames = list(queue)
        queue.clear()
        return frames

    def close(self, room_id: str) -> None:
        for host in (True, False):
            ws = self._conns.pop((room_id, host), None)
            if ws is not None:
                try:
                    self._run(ws.close())
                except Exception:
                    pass
        self._deadline.pop(room_id, None)

    def has_room(self, room_id: str) -> bool:
        ws = self._conns.get((room_id, True))
        return ws is not None and getattr(ws, "close_code", None) is None and self._deadline.get(room_id, 0) > time.time()

    def shutdown(self) -> None:
        for room_id in {r for r, _ in list(self._conns)}:
            self.close(room_id)
        self._loop.call_soon_threadsafe(self._loop.stop)
