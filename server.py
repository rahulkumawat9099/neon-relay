"""Neon Royale relay server (pure Python, no extra packages).
Host aur players isse WebSocket se connect karte hain; yeh unke beech packets forward karta hai.
Run: python server.py   (PORT env variable use hota hai, default 8080)"""
import asyncio, base64, hashlib, json, os, random, struct

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
CHARS = "ABCDEFGHJKMNPQRSTVWXYZ23456789"
MAX_PAYLOAD = 1 << 20
MAX_ROOMS = 500
MAX_CLIENTS = 14
rooms = {}


class Conn:
    def __init__(self, writer):
        self.w = writer
        self.closed = False

    def _frame(self, op, payload):
        n = len(payload)
        if n < 126:
            head = struct.pack("!BB", 0x80 | op, n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | op, 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | op, 127, n)
        return head + payload

    def send(self, op, payload):
        if self.closed:
            return
        try:
            if self.w.transport.get_write_buffer_size() > 4 * 1024 * 1024:
                self.close()
                return
            self.w.write(self._frame(op, payload))
        except Exception:
            self.closed = True

    def send_text(self, s):
        self.send(1, s.encode())

    def send_json(self, d):
        self.send_text(json.dumps(d))

    def send_bytes(self, b):
        self.send(2, b)

    def close(self):
        if not self.closed:
            self.send(8, b"")
            self.closed = True
            try:
                self.w.close()
            except Exception:
                pass


async def read_message(reader, conn):
    """Returns (opcode, data) for text/binary messages, (None, None) on close."""
    buf = b""
    first_op = None
    while True:
        h = await reader.readexactly(2)
        fin = h[0] & 0x80
        op = h[0] & 0x0F
        masked = h[1] & 0x80
        n = h[1] & 0x7F
        if n == 126:
            n = int.from_bytes(await reader.readexactly(2), "big")
        elif n == 127:
            n = int.from_bytes(await reader.readexactly(8), "big")
        if n > MAX_PAYLOAD:
            raise ValueError("too big")
        mask = await reader.readexactly(4) if masked else b""
        data = await reader.readexactly(n) if n else b""
        if masked and n:
            m = (mask * (n // 4 + 1))[:n]
            data = (int.from_bytes(data, "big") ^ int.from_bytes(m, "big")).to_bytes(n, "big")
        if op == 8:
            return None, None
        if op == 9:
            conn.send(10, data)
            continue
        if op == 10:
            continue
        if op in (1, 2):
            first_op = op
            buf = data
        elif op == 0:
            buf += data
        if len(buf) > MAX_PAYLOAD:
            raise ValueError("too big")
        if fin:
            return first_op, buf


def new_code():
    for _ in range(100):
        c = "".join(random.choice(CHARS) for _ in range(5))
        if c not in rooms:
            return c
    return None


def everyone(room):
    return [(1, room["host"])] + list(room["clients"].items())


async def session(reader, writer):
    conn = Conn(writer)
    room = None
    my_id = 0
    is_host = False

    async def pinger():
        while not conn.closed:
            await asyncio.sleep(20)
            conn.send(9, b"")

    ptask = asyncio.create_task(pinger())
    try:
        while True:
            op, data = await read_message(reader, conn)
            if op is None:
                break
            if op == 1:
                try:
                    d = json.loads(data.decode())
                except Exception:
                    continue
                t = d.get("t")
                if t == "host" and room is None:
                    if len(rooms) >= MAX_ROOMS:
                        conn.send_json({"t": "err", "m": "Server full hai, baad me try karo."})
                        continue
                    code = new_code()
                    room = {"code": code, "host": conn, "clients": {}, "open": True}
                    rooms[code] = room
                    is_host = True
                    my_id = 1
                    conn.send_json({"t": "hosted", "code": code})
                elif t == "join" and room is None:
                    r = rooms.get(str(d.get("code", "")).strip().upper())
                    if r is None or not r["open"]:
                        conn.send_json({"t": "err", "m": "Room nahi mila (code galat hai ya match shuru ho chuka)."})
                        continue
                    if len(r["clients"]) >= MAX_CLIENTS:
                        conn.send_json({"t": "err", "m": "Room full hai."})
                        continue
                    my_id = random.randint(2, 2**30)
                    while my_id in r["clients"]:
                        my_id = random.randint(2, 2**30)
                    others = list(r["clients"].keys())
                    r["clients"][my_id] = conn
                    room = r
                    conn.send_json({"t": "joined", "id": my_id, "peers": [1] + others})
                    for pid, c in everyone(r):
                        if pid != my_id:
                            c.send_json({"t": "peer_join", "id": my_id})
                elif t == "close_room" and is_host and room:
                    room["open"] = False
            elif op == 2 and room is not None and len(data) >= 5:
                target = struct.unpack("<i", data[:4])[0]
                out = struct.pack("<I", my_id) + data[4:]
                for pid, c in everyone(room):
                    if pid == my_id:
                        continue
                    if target == 0 or (target < 0 and pid != -target) or target == pid:
                        c.send_bytes(out)
    except (asyncio.IncompleteReadError, ConnectionError, ValueError, OSError):
        pass
    finally:
        ptask.cancel()
        if room is not None:
            if is_host:
                rooms.pop(room["code"], None)
                for c in list(room["clients"].values()):
                    c.send_json({"t": "room_closed"})
                    c.close()
            else:
                room["clients"].pop(my_id, None)
                for pid, c in everyone(room):
                    c.send_json({"t": "peer_leave", "id": my_id})
        conn.close()


async def handle(reader, writer):
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 15)
    except Exception:
        writer.close()
        return
    lines = head.decode("latin1").split("\r\n")
    headers = {}
    for l in lines[1:]:
        if ":" in l:
            k, v = l.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    if headers.get("upgrade", "").lower() != "websocket" or "sec-websocket-key" not in headers:
        body = ("Neon Royale relay OK | rooms: %d\n" % len(rooms)).encode()
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
        try:
            await writer.drain()
        except Exception:
            pass
        writer.close()
        return
    accept = base64.b64encode(hashlib.sha1((headers["sec-websocket-key"] + GUID).encode()).digest()).decode()
    writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n" % accept).encode())
    await writer.drain()
    await session(reader, writer)


async def main():
    port = int(os.environ.get("PORT", "8080"))
    server = await asyncio.start_server(handle, "0.0.0.0", port)
    print("Relay server chal raha hai, port", port, flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
