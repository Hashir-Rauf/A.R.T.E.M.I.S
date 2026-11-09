"""A runnable relay with the same rules as the cloud Worker, for use on a home network or for tests.

    python -m artemis.remote.edge.server --port 8765

It serves the phone page at "/" and relays WebSocket frames at /room/<id>. It holds a one-way
proof per room, a counter of wrong guesses, and frames it cannot read. Frames for a side that
is not connected yet wait in a short queue, so the host's hello is there when the device joins.
Both ends connect out to it; ARTEMIS opens no port.
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import time
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from websockets.asyncio.server import serve
from websockets.http11 import Response

PWA = Path(__file__).parent / "pwa"
MAX_TRIES = 5
MAX_QUEUE = 64


class _Room:
    def __init__(self, proof: str, expires: float) -> None:
        self.proof = proof
        self.expires = expires
        self.tries = 0
        self.closed = False
        self.host = None
        self.device = None
        self.to_host: list[bytes] = []
        self.to_device: list[bytes] = []


class RelayServer:
    def __init__(self) -> None:
        self.rooms: dict[str, _Room] = {}

    async def handler(self, ws) -> None:
        parsed = urlparse(ws.request.path)
        parts = parsed.path.strip("/").split("/")
        query = parse_qs(parsed.query)
        role = (query.get("role") or [""])[0]
        proof = (query.get("proof") or [""])[0]
        if len(parts) != 2 or parts[0] != "room" or role not in ("host", "device"):
            await ws.close(4004, "not found")
            return
        room = self.rooms.get(parts[1])
        now = time.time()
        if role == "host":
            if room is None or room.closed or room.expires < now:
                ttl = min(float((query.get("ttl") or ["300"])[0]), 86400 * 365)
                room = _Room(proof, now + ttl)
                self.rooms[parts[1]] = room
            elif not hmac.compare_digest(room.proof, proof):
                await ws.close(4003, "refused")
                return
        else:
            if room is None or room.closed or room.expires < now:
                await ws.close(4010, "closed")
                return
            if not hmac.compare_digest(room.proof, proof):
                room.tries += 1
                if room.tries >= MAX_TRIES:
                    room.closed = True
                await ws.close(4003, "refused")
                return
        mine, theirs = ("host", "device") if role == "host" else ("device", "host")
        setattr(room, mine, ws)
        inbox = room.to_host if role == "host" else room.to_device
        for frame in list(inbox):
            await ws.send(frame)
        inbox.clear()
        try:
            async for frame in ws:
                if isinstance(frame, str):
                    frame = frame.encode()
                other = getattr(room, theirs)
                if other is not None:
                    try:
                        await other.send(frame)
                        continue
                    except Exception:
                        setattr(room, theirs, None)
                queue = room.to_device if role == "host" else room.to_host
                if len(queue) < MAX_QUEUE:
                    queue.append(frame)  # opaque: held, never read
        finally:
            if getattr(room, mine) is ws:
                setattr(room, mine, None)

    async def static(self, connection, request):
        """Serve the phone page; anything that is not a WebSocket upgrade."""
        if request.headers.get("Upgrade", "").lower() == "websocket":
            return None
        path = urlparse(request.path).path
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (PWA / name).resolve()
        if PWA.resolve() not in target.parents or not target.is_file():
            return Response(HTTPStatus.NOT_FOUND, "Not Found", websockets_headers(), b"Not found")
        kind = {"html": "text/html", "js": "text/javascript", "json": "application/json", "svg": "image/svg+xml"}.get(
            target.suffix.lstrip("."), "application/octet-stream"
        )
        return Response(
            HTTPStatus.OK, "OK", websockets_headers(("Content-Type", f"{kind}; charset=utf-8")),
            target.read_bytes(),
        )


def websockets_headers(*items):
    from websockets.datastructures import Headers

    return Headers(list(items))


async def run(host: str = "127.0.0.1", port: int = 8765, ready: asyncio.Event | None = None):
    server = RelayServer()
    async with serve(server.handler, host, port, process_request=server.static) as running:
        if ready is not None:
            ready.set()
        await running.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="ARTEMIS remote relay")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"Relay on http://{args.host}:{args.port}  (phone page at /)")
    asyncio.run(run(args.host, args.port))


if __name__ == "__main__":
    main()
