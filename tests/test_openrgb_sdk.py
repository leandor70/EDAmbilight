"""OpenRGB SDK client, checked against a small fake server that speaks the protocol."""

import socket
import struct
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core import openrgb_sdk as sdk  # noqa: E402


# ── A fake OpenRGB server, built independently from the client ─────────────────

def _s(text):
    raw = text.encode() + b"\x00"
    return struct.pack("<H", len(raw)) + raw


def _col(r, g, b):
    return bytes((r, g, b, 0))


def _mode(name, value, version):
    out = _s(name) + struct.pack("<iIII", value, 0x1A0, 0, 100)
    if version >= 3:
        out += struct.pack("<II", 0, 100)
    out += struct.pack("<III", 0, 0, 50)
    if version >= 3:
        out += struct.pack("<I", 80)
    out += struct.pack("<II", 0, 1)
    out += struct.pack("<H", 1) + _col(1, 2, 3)
    return out


def _zone(name, count, version, matrix=None, segments=()):
    out = _s(name) + struct.pack("<iIII", 1, count, count, count)
    if matrix:
        h, w = matrix
        out += struct.pack("<H", 8 + 4 * h * w) + struct.pack("<II", h, w) + b"\x00" * (4 * h * w)
    else:
        out += struct.pack("<H", 0)
    if version >= 4:
        out += struct.pack("<H", len(segments))
        for seg_name, start, n in segments:
            out += _s(seg_name) + struct.pack("<iII", 0, start, n)
    return out


def controller(version, name="Strip", dev_type=4):
    body = struct.pack("<i", dev_type) + _s(name)
    if version >= 1:
        body += _s("Vendor")
    body += _s("desc") + _s("1.0") + _s("serial") + _s("loc")
    body += struct.pack("<Hi", 2, 1)
    body += _mode("Direct", 0, version) + _mode("Static", 1, version)
    body += struct.pack("<H", 2)
    body += _zone("Top", 3, version, segments=[("T1", 0, 1), ("T2", 1, 2)])
    body += _zone("Matrix", 4, version, matrix=(2, 2))
    body += struct.pack("<H", 7)
    for i in range(7):
        body += _s(f"LED {i}") + struct.pack("<I", i)
    body += struct.pack("<H", 7) + b"".join(_col(i, i, i) for i in range(7))
    return struct.pack("<I", 4 + len(body)) + body


class FakeServer:
    def __init__(self, server_version=5, announce_change=False, answer_version=True):
        self.server_version = server_version
        self.announce_change = announce_change
        self.answer_version = answer_version
        self.received = []                      # (device, command, payload)
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self.port = self._listener.getsockname()[1]
        self.version = 0
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        try:
            conn, _ = self._listener.accept()
        except OSError:
            return
        with conn:
            while True:
                head = self._read(conn, 16)
                if head is None:
                    return
                magic, dev, cmd, size = struct.unpack("<4sIII", head)
                assert magic == b"ORGB"
                payload = self._read(conn, size) if size else b""
                self.received.append((dev, cmd, payload))
                if cmd == 40:
                    if self.answer_version:
                        self.version = min(self.server_version, struct.unpack("<I", payload)[0])
                        self._reply(conn, 0, 40, struct.pack("<I", self.server_version))
                elif cmd == 0:
                    if self.announce_change:
                        self._reply(conn, 0, 51, b"")
                    self._reply(conn, 0, 0, struct.pack("<I", 2))
                elif cmd == 1:
                    self._reply(conn, dev, 1, controller(self.version, "Strip" if dev == 0 else "Board",
                                                         4 if dev == 0 else 0))

    @staticmethod
    def _read(conn, n):
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    @staticmethod
    def _reply(conn, dev, cmd, payload):
        conn.sendall(struct.pack("<4sIII", b"ORGB", dev, cmd, len(payload)) + payload)

    def commands(self, cmd):
        return [(d, p) for d, c, p in self.received if c == cmd]

    def close(self):
        self._listener.close()


@pytest.fixture
def server():
    srv = FakeServer()
    yield srv
    srv.close()


def _wait(cond, timeout=2.0):
    import time
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_reads_the_device_list(server):
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        assert client.protocol_version == 4          # capped at what we can parse
        assert [d.name for d in client.devices] == ["Strip", "Board"]
        strip, board = client.devices
        assert strip.type is sdk.DeviceType.LEDSTRIP
        assert board.type is sdk.DeviceType.MOTHERBOARD
        assert strip.vendor == "Vendor"
        assert len(strip.leds) == 7
        assert [m.name for m in strip.modes] == ["Direct", "Static"]
        assert strip.modes[0].brightness_max == 100 and strip.modes[0].colors[0] == (1, 2, 3)
        top, matrix = strip.zones
        assert (top.name, len(top.leds)) == ("Top", 3)
        assert [(s.name, s.leds_count) for s in top.segments] == [("T1", 1), ("T2", 2)]
        assert matrix.matrix == (2, 2) and [l.name for l in matrix.leds] == ["LED 3", "LED 4", "LED 5", "LED 6"]


def test_names_the_client(server):
    with sdk.OpenRGBClient("127.0.0.1", server.port):
        pass
    assert server.commands(50)[0][1] == b"EDAmbilight\x00"


@pytest.mark.parametrize("server_version", [0, 1, 3])
def test_older_servers_are_parsed(server_version):
    srv = FakeServer(server_version=server_version, answer_version=server_version > 0)
    try:
        with sdk.OpenRGBClient("127.0.0.1", srv.port, timeout=3.0) as client:
            assert client.protocol_version == server_version
            assert [d.name for d in client.devices] == ["Strip", "Board"]
            assert len(client.devices[0].leds) == 7
            assert len(client.devices[0].zones) == 2
            if server_version == 0:
                assert client.devices[0].vendor == ""
    finally:
        srv.close()


def test_device_list_announcement_is_skipped_and_flagged():
    srv = FakeServer(announce_change=True)
    try:
        with sdk.OpenRGBClient("127.0.0.1", srv.port) as client:
            assert len(client.devices) == 2
    finally:
        srv.close()


def test_set_colors_sends_one_update_leds_packet(server):
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        client.devices[0].set_colors([(i, 10 + i, 20 + i) for i in range(7)])
        assert _wait(lambda: server.commands(1050))
    dev, payload = server.commands(1050)[0]
    assert dev == 0
    size, count = struct.unpack_from("<IH", payload)
    assert size == len(payload) == 4 + 2 + 7 * 4 and count == 7
    assert payload[6:10] == bytes((0, 10, 20, 0))
    assert payload[-4:] == bytes((6, 16, 26, 0))


def test_set_colors_needs_one_color_per_led(server):
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        with pytest.raises(ValueError, match="doesn't match"):
            client.devices[0].set_colors([(0, 0, 0)] * 3)


def test_set_mode_sends_the_whole_mode(server):
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        client.devices[0].set_mode("direct")
        assert client.devices[0].active_mode == 0
        client.devices[0].set_mode("Static")
        assert _wait(lambda: len(server.commands(1101)) == 2)
    _, first = server.commands(1101)[0]
    size, mode_index = struct.unpack_from("<II", first)
    assert size == len(first) and mode_index == 0
    assert first[8:] == _mode("Direct", 0, 4)         # same bytes the server sent
    assert struct.unpack_from("<I", server.commands(1101)[1][1], 4)[0] == 1


def test_unknown_mode_is_an_error(server):
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        with pytest.raises(ValueError):
            client.devices[0].set_mode("Rainbow Wave")


def test_unknown_device_type_does_not_break_the_list():
    assert sdk.DeviceType(99) is sdk.DeviceType.UNKNOWN


def test_connection_refused_is_a_readable_error():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    with pytest.raises(sdk.OpenRGBError, match="Cannot connect"):
        sdk.OpenRGBClient("127.0.0.1", port, timeout=1.0)


def test_write_after_close_is_an_error(server):
    client = sdk.OpenRGBClient("127.0.0.1", server.port)
    dev = client.devices[0]
    client.close()
    with pytest.raises(sdk.OpenRGBError):
        dev.set_colors([(0, 0, 0)] * 7)
