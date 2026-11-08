// DRAFT, NOT DEPLOYED, NOT TESTED. The cloud edge for ARTEMIS remote access.
//
// It does what src/artemis/remote/relay.py does, which is the version the tests run:
//   * one Durable Object per room (a pairing, or a paired device);
//   * the host opens the room with a one-way proof; a device must present the same proof;
//   * after five wrong proofs the room closes;
//   * every frame is forwarded as opaque bytes. It is never parsed, stored or logged.
// It holds no code, no key and no message in the clear. Both ends connect OUT to it, so
// the computer running ARTEMIS needs no inbound port.
//
// Deploy with Wrangler once you have chosen a Cloudflare account. Routes:
//   GET /room/<id>?role=host&proof=<hex>&ttl=<seconds>   host opens (first caller) and listens
//   GET /room/<id>?role=device&proof=<hex>               device joins, if the proof matches
// Both upgrade to a WebSocket. Binary frames are relayed to the other side.

const MAX_TRIES = 5;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const match = url.pathname.match(/^\/room\/([A-Za-z0-9:_-]{1,64})$/);
    if (!match || request.headers.get("Upgrade") !== "websocket") {
      return new Response("Not found", { status: 404 });
    }
    const stub = env.ROOMS.get(env.ROOMS.idFromName(match[1]));
    return stub.fetch(request);
  },
};

export class Room {
  constructor(state) {
    this.state = state; // durable: proof, expiry, tries. Never message content.
    this.host = null;
    this.device = null;
  }

  async fetch(request) {
    const url = new URL(request.url);
    const role = url.searchParams.get("role");
    const proof = url.searchParams.get("proof") || "";
    let room = await this.state.storage.get("room");
    const now = Date.now();

    if (role === "host") {
      if (!room) {
        const ttl = Math.min(Number(url.searchParams.get("ttl")) || 300, 86400) * 1000;
        room = { proof, expires: now + ttl, tries: 0, closed: false };
        await this.state.storage.put("room", room);
      } else if (room.proof !== proof) {
        return new Response("Refused", { status: 403 });
      }
    } else {
      if (!room || room.closed || room.expires < now) return new Response("Closed", { status: 410 });
      if (room.proof !== proof) {
        room.tries += 1;
        if (room.tries >= MAX_TRIES) room.closed = true;
        await this.state.storage.put("room", room);
        return new Response("Refused", { status: 403 });
      }
    }

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    server.accept();
    if (role === "host") this.host = server; else this.device = server;
    server.addEventListener("message", (event) => {
      const other = role === "host" ? this.device : this.host;
      if (other) other.send(event.data); // opaque: forwarded, never read
    });
    server.addEventListener("close", () => {
      if (role === "host") this.host = null; else this.device = null;
    });
    return new Response(null, { status: 101, webSocket: client });
  }
}
