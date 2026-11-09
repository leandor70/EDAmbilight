"""
Minimal client for the OpenRGB SDK server (TCP, default port 6742).

Written from the public protocol description of the OpenRGB SDK
(https://gitlab.com/CalcProgrammer1/OpenRGB/-/wikis/OpenRGB-SDK-Documentation),
so EDAmbilight does not depend on a third-party client library.

Only what the application needs is implemented:
  - connect, negotiate the protocol version, name the client
  - read the device list (name, type, modes, zones, segments, LEDs)
  - switch a device to a mode (e.g. "Direct")
  - write LED colors, for the whole device

Every packet is a 16-byte header followed by a payload, all little-endian:

    "ORGB" | device index u32 | command u32 | payload size u32
"""

from __future__ import annotations

import socket
import struct
import threading
from enum import IntEnum
from typing import List, NamedTuple, Optional, Sequence, Tuple

DEFAULT_PORT = 6742
CLIENT_NAME = "EDAmbilight"

# Highest protocol version this client can parse. The server answers with the
# lower of the two, so newer servers still talk to us.
MAX_PROTOCOL_VERSION = 4

_MAGIC = b"ORGB"
_HEADER = struct.Struct("<4sIII")

CMD_REQUEST_CONTROLLER_COUNT = 0
CMD_REQUEST_CONTROLLER_DATA = 1
CMD_REQUEST_PROTOCOL_VERSION = 40
CMD_SET_CLIENT_NAME = 50
CMD_DEVICE_LIST_UPDATED = 51
CMD_RGBCONTROLLER_UPDATELEDS = 1050
CMD_RGBCONTROLLER_SETCUSTOMMODE = 1100
CMD_RGBCONTROLLER_UPDATEMODE = 1101


class OpenRGBError(Exception):
    """Connection or protocol problem with the OpenRGB server."""


class DeviceType(IntEnum):
    MOTHERBOARD = 0
    DRAM = 1
    GPU = 2
    COOLER = 3
    LEDSTRIP = 4
    KEYBOARD = 5
    MOUSE = 6
    MOUSEMAT = 7
    HEADSET = 8
    HEADSET_STAND = 9
    GAMEPAD = 10
    LIGHT = 11
    SPEAKER = 12
    VIRTUAL = 13
    STORAGE = 14
    CASE = 15
    MICROPHONE = 16
    ACCESSORY = 17
    KEYPAD = 18
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value):
        # A device type added by a newer OpenRGB must not break the device list.
        return cls.UNKNOWN


class RGBColor(NamedTuple):
    r: int
    g: int
    b: int


# ── Data model ─────────────────────────────────────────────────────────────────


class LED:
    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value


class Segment:
    def __init__(self, name: str, type_: int, start_idx: int, leds_count: int) -> None:
        self.name = name
        self.type = type_
        self.start_idx = start_idx
        self.leds_count = leds_count


NO_LED = 0xFFFFFFFF      # an empty cell in a zone's matrix map


class Zone:
    def __init__(self, name: str, type_: int, leds_min: int, leds_max: int,
                 leds_count: int, matrix: Optional[Tuple[int, int]],
                 segments: List[Segment],
                 matrix_map: Optional[List[List[int]]] = None) -> None:
        self.name = name
        self.type = type_
        self.leds_min = leds_min
        self.leds_max = leds_max
        self.leds_count = leds_count
        self.matrix = matrix              # (height, width) or None
        # matrix_map[row][col] = LED index inside the zone, or NO_LED for an empty cell
        self.matrix_map = matrix_map
        self.segments = segments
        self.leds: List[LED] = []         # filled in by Device, in hardware order


class Mode:
    def __init__(self, name: str, value: int, flags: int, speed_min: int, speed_max: int,
                 brightness_min: int, brightness_max: int, colors_min: int, colors_max: int,
                 speed: int, brightness: int, direction: int, color_mode: int,
                 colors: List[RGBColor]) -> None:
        self.name = name
        self.value = value
        self.flags = flags
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.colors_min = colors_min
        self.colors_max = colors_max
        self.speed = speed
        self.brightness = brightness
        self.direction = direction
        self.color_mode = color_mode
        self.colors = colors


class Device:
    """One RGB controller as reported by the server."""

    def __init__(self, client: "OpenRGBClient", index: int) -> None:
        self._client = client
        self.id = index
        self.type: DeviceType = DeviceType.UNKNOWN
        self.name = ""
        self.vendor = ""
        self.description = ""
        self.version = ""
        self.serial = ""
        self.location = ""
        self.modes: List[Mode] = []
        self.active_mode = 0
        self.zones: List[Zone] = []
        self.leds: List[LED] = []
        self.colors: List[RGBColor] = []

    def __repr__(self) -> str:
        return f"<Device {self.id} {self.name!r} {self.type.name} leds={len(self.leds)}>"

    # ── Commands ───────────────────────────────────────────────────────────────

    def set_mode(self, mode_name: str) -> None:
        """Activate the mode with this name (case-insensitive), e.g. "direct".

        Raises ValueError when the device has no such mode.
        """
        wanted = mode_name.strip().lower()
        for idx, mode in enumerate(self.modes):
            if mode.name.strip().lower() == wanted:
                self._client._send_update_mode(self.id, idx, mode)
                self.active_mode = idx
                return
        raise ValueError(f"{self.name!r} has no mode {mode_name!r}")

    def set_custom_mode(self) -> None:
        """Let the server pick the mode for per-LED control."""
        self._client._send(self.id, CMD_RGBCONTROLLER_SETCUSTOMMODE, b"")

    def set_colors(self, colors: Sequence[Sequence[int]]) -> None:
        """Set every LED of the device. Needs exactly one color per LED."""
        if len(colors) != len(self.leds):
            raise ValueError(
                f"Number of colors ({len(colors)}) doesn't match number of LEDs ({len(self.leds)})"
            )
        self._client._send_colors(self.id, colors)
        self.colors = [RGBColor(int(c[0]), int(c[1]), int(c[2])) for c in colors]


# ── Wire format helpers ────────────────────────────────────────────────────────


class _Reader:
    """Sequential little-endian reader over a controller-data payload."""

    def __init__(self, data: bytes) -> None:
        self._d = data
        self.pos = 0

    def _take(self, fmt: str):
        size = struct.calcsize(fmt)
        if self.pos + size > len(self._d):
            raise OpenRGBError("Truncated data from the OpenRGB server")
        (value,) = struct.unpack_from(fmt, self._d, self.pos)
        self.pos += size
        return value

    def u16(self) -> int:
        return self._take("<H")

    def u32(self) -> int:
        return self._take("<I")

    def i32(self) -> int:
        return self._take("<i")

    def skip(self, n: int) -> None:
        if self.pos + n > len(self._d):
            raise OpenRGBError("Truncated data from the OpenRGB server")
        self.pos += n

    def string(self) -> str:
        """u16 length (terminator included) followed by that many bytes."""
        n = self.u16()
        if self.pos + n > len(self._d):
            raise OpenRGBError("Truncated data from the OpenRGB server")
        raw = self._d[self.pos:self.pos + n]
        self.pos += n
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

    def color(self) -> RGBColor:
        r, g, b = self._d[self.pos], self._d[self.pos + 1], self._d[self.pos + 2]
        self.skip(4)                       # the fourth byte is padding
        return RGBColor(r, g, b)


def _pack_string(text: str) -> bytes:
    raw = text.encode("utf-8") + b"\x00"
    return struct.pack("<H", len(raw)) + raw


def _pack_colors(colors: Sequence[Sequence[int]]) -> bytes:
    out = bytearray()
    for c in colors:
        out += bytes((int(c[0]) & 255, int(c[1]) & 255, int(c[2]) & 255, 0))
    return bytes(out)


def _read_mode(r: _Reader, version: int) -> Mode:
    name = r.string()
    value = r.i32()
    flags = r.u32()
    speed_min = r.u32()
    speed_max = r.u32()
    brightness_min = brightness_max = 0
    if version >= 3:
        brightness_min = r.u32()
        brightness_max = r.u32()
    colors_min = r.u32()
    colors_max = r.u32()
    speed = r.u32()
    brightness = r.u32() if version >= 3 else 0
    direction = r.u32()
    color_mode = r.u32()
    colors = [r.color() for _ in range(r.u16())]
    return Mode(name, value, flags, speed_min, speed_max, brightness_min, brightness_max,
                colors_min, colors_max, speed, brightness, direction, color_mode, colors)


def _pack_mode(mode: Mode, version: int) -> bytes:
    out = bytearray()
    out += _pack_string(mode.name)
    out += struct.pack("<iII", mode.value, mode.flags, mode.speed_min)
    out += struct.pack("<I", mode.speed_max)
    if version >= 3:
        out += struct.pack("<II", mode.brightness_min, mode.brightness_max)
    out += struct.pack("<III", mode.colors_min, mode.colors_max, mode.speed)
    if version >= 3:
        out += struct.pack("<I", mode.brightness)
    out += struct.pack("<II", mode.direction, mode.color_mode)
    out += struct.pack("<H", len(mode.colors))
    out += _pack_colors(mode.colors)
    return bytes(out)


def _read_zone(r: _Reader, version: int) -> Zone:
    name = r.string()
    type_ = r.i32()
    leds_min = r.u32()
    leds_max = r.u32()
    leds_count = r.u32()
    matrix = None
    matrix_map = None
    matrix_len = r.u16()
    if matrix_len:
        height = r.u32()
        width = r.u32()
        matrix_map = [[r.u32() for _ in range(width)] for _ in range(height)]
        matrix = (height, width)
    segments: List[Segment] = []
    if version >= 4:
        for _ in range(r.u16()):
            seg_name = r.string()
            seg_type = r.i32()
            start = r.u32()
            count = r.u32()
            segments.append(Segment(seg_name, seg_type, start, count))
    return Zone(name, type_, leds_min, leds_max, leds_count, matrix, segments, matrix_map)


def parse_controller(data: bytes, index: int, version: int, client: "OpenRGBClient") -> Device:
    """Build a Device from the payload of a REQUEST_CONTROLLER_DATA reply."""
    r = _Reader(data)
    r.u32()                                    # total size, includes itself
    dev = Device(client, index)
    dev.type = DeviceType(r.i32())
    dev.name = r.string()
    if version >= 1:
        dev.vendor = r.string()
    dev.description = r.string()
    dev.version = r.string()
    dev.serial = r.string()
    dev.location = r.string()

    num_modes = r.u16()
    dev.active_mode = r.i32()
    dev.modes = [_read_mode(r, version) for _ in range(num_modes)]

    dev.zones = [_read_zone(r, version) for _ in range(r.u16())]

    dev.leds = []
    for _ in range(r.u16()):
        led_name = r.string()
        dev.leds.append(LED(led_name, r.u32()))

    dev.colors = [r.color() for _ in range(r.u16())]

    # A zone owns the next `leds_count` LEDs of the device, in order.
    offset = 0
    for zone in dev.zones:
        zone.leds = dev.leds[offset:offset + zone.leds_count]
        offset += zone.leds_count
    return dev


# ── Client ─────────────────────────────────────────────────────────────────────


class OpenRGBClient:
    """Connection to an OpenRGB SDK server.

    Connecting reads the whole device list into `devices`. Writes are thread
    safe; each call sends one packet and does not wait for a reply.
    """

    def __init__(self, address: str = "127.0.0.1", port: int = DEFAULT_PORT,
                 name: str = CLIENT_NAME, timeout: float = 5.0) -> None:
        self.address = address
        self.port = int(port)
        self.timeout = timeout
        self.protocol_version = 0
        self.devices: List[Device] = []
        self.device_list_changed = False   # the server announced a hardware change
        self._lock = threading.Lock()
        self._sock: Optional[socket.socket] = None

        try:
            self._sock = socket.create_connection((self.address, self.port), timeout=timeout)
        except OSError as exc:
            raise OpenRGBError(f"Cannot connect to OpenRGB at {self.address}:{self.port}: {exc}") from exc
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock.settimeout(timeout)

        try:
            self._negotiate_version()
            self._send(0, CMD_SET_CLIENT_NAME, name.encode("utf-8") + b"\x00")
            self.refresh()
        except Exception:
            self.close()
            raise

    # ── Connection ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    disconnect = close

    def __enter__(self) -> "OpenRGBClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def refresh(self) -> None:
        """Read the device list again from the server."""
        payload = self._request(0, CMD_REQUEST_CONTROLLER_COUNT, b"", CMD_REQUEST_CONTROLLER_COUNT)
        (count,) = struct.unpack_from("<I", payload)
        devices = []
        for idx in range(count):
            request = struct.pack("<I", self.protocol_version) if self.protocol_version >= 1 else b""
            data = self._request(idx, CMD_REQUEST_CONTROLLER_DATA, request, CMD_REQUEST_CONTROLLER_DATA)
            devices.append(parse_controller(data, idx, self.protocol_version, self))
        self.devices = devices
        self.device_list_changed = False

    def _negotiate_version(self) -> None:
        """Offer our highest version; a server too old to answer means version 0."""
        try:
            payload = self._request(0, CMD_REQUEST_PROTOCOL_VERSION,
                                    struct.pack("<I", MAX_PROTOCOL_VERSION),
                                    CMD_REQUEST_PROTOCOL_VERSION, timeout=1.0)
            (server_version,) = struct.unpack_from("<I", payload)
            self.protocol_version = min(server_version, MAX_PROTOCOL_VERSION)
        except socket.timeout:
            self.protocol_version = 0

    # ── Packets ────────────────────────────────────────────────────────────────

    def _send(self, device_index: int, command: int, payload: bytes) -> None:
        packet = _HEADER.pack(_MAGIC, device_index, command, len(payload)) + payload
        with self._lock:
            if self._sock is None:
                raise OpenRGBError("Connection to OpenRGB is closed")
            try:
                self._sock.sendall(packet)
            except OSError as exc:
                raise OpenRGBError(f"Lost connection to OpenRGB: {exc}") from exc

    def _recv_exact(self, n: int) -> bytes:
        chunks = []
        while n:
            chunk = self._sock.recv(n)
            if not chunk:
                raise OpenRGBError("OpenRGB closed the connection")
            chunks.append(chunk)
            n -= len(chunk)
        return b"".join(chunks)

    def _request(self, device_index: int, command: int, payload: bytes,
                 reply_command: int, timeout: Optional[float] = None) -> bytes:
        """Send a packet and return the payload of the matching reply.

        Packets the server sends on its own (device list changed) are noted and
        skipped while waiting.
        """
        packet = _HEADER.pack(_MAGIC, device_index, command, len(payload)) + payload
        with self._lock:
            if self._sock is None:
                raise OpenRGBError("Connection to OpenRGB is closed")
            previous = self._sock.gettimeout()
            if timeout is not None:
                self._sock.settimeout(timeout)
            try:
                self._sock.sendall(packet)
                while True:
                    magic, _idx, cmd, size = _HEADER.unpack(self._recv_exact(_HEADER.size))
                    if magic != _MAGIC:
                        raise OpenRGBError("Unexpected data from the OpenRGB server")
                    body = self._recv_exact(size) if size else b""
                    if cmd == CMD_DEVICE_LIST_UPDATED:
                        self.device_list_changed = True
                        continue
                    if cmd == reply_command:
                        return body
            except socket.timeout:
                raise
            except OSError as exc:
                raise OpenRGBError(f"Lost connection to OpenRGB: {exc}") from exc
            finally:
                if self._sock is not None:
                    self._sock.settimeout(previous)

    def _send_colors(self, device_index: int, colors: Sequence[Sequence[int]]) -> None:
        body = struct.pack("<H", len(colors)) + _pack_colors(colors)
        self._send(device_index, CMD_RGBCONTROLLER_UPDATELEDS, struct.pack("<I", 4 + len(body)) + body)

    def _send_update_mode(self, device_index: int, mode_index: int, mode: Mode) -> None:
        body = struct.pack("<I", mode_index) + _pack_mode(mode, self.protocol_version)
        self._send(device_index, CMD_RGBCONTROLLER_UPDATEMODE, struct.pack("<I", 4 + len(body)) + body)
