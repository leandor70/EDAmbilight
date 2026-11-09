"""
OpenRGBManager — simplified manager per EDAmbilight.

Interfaccia minimale compatibile con AmbilightService:
  - apply_direct_colors(device_key, colors)
  - is_effect_playing() -> sempre False (no effects in this app)
  - devices: lista di DeviceController
  - _make_device_key(ctrl) -> str
"""

import threading
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class TopologyType(Enum):
    MATRIX = "matrix"
    LINEAR = "linear"
    SINGLE = "single"


@dataclass
class DeviceTopology:
    device: object        # openrgb device object
    topology_type: TopologyType
    led_count: int


class DeviceController:
    def __init__(self, device, topology_type: TopologyType):
        self.topology = DeviceTopology(
            device=device,
            topology_type=topology_type,
            led_count=len(device.leds),
        )
        # Assigned by OpenRGBManager._assign_device_keys() — disambiguates
        # devices that share the same name (e.g. two identical RAM modules).
        self.device_key: str = ""


class OpenRGBManager:
    """
    Manages OpenRGB devices for ambilight-only use.
    No effect system — just direct LED color control.
    """

    def __init__(self, client) -> None:
        self._client = client
        self._lock   = threading.Lock()
        self.devices: List[DeviceController] = []
        self._init_devices()

    # ── Device enumeration ─────────────────────────────────────────────────────

    def _init_devices(self) -> None:
        """Enumerate every device OpenRGB reports (keyboards included: the user
        decides in the Devices page whether one takes part in the ambilight)."""
        for device in self._client.devices:
            self.devices.append(DeviceController(device, self._detect_topology(device)))
        self._assign_device_keys()
        print(f"[OpenRGBManager] {len(self.devices)} devices enrolled "
              f"({len(self._client.devices)} total from OpenRGB)")

    def _assign_device_keys(self) -> None:
        """Give each device a stable key. Devices sharing the same name+type
        (e.g. two identical RAM modules) would otherwise collide on one key,
        making one of them unreachable and duplicating its topology zones.
        The first occurrence keeps the bare 'name::type' key (backward
        compatible); each further duplicate gets a '#N' suffix."""
        seen: dict = {}
        for ctrl in self.devices:
            base = f"{ctrl.topology.device.name}::{ctrl.topology.topology_type.value}"
            n = seen.get(base, 0)
            seen[base] = n + 1
            ctrl.device_key = base if n == 0 else f"{base}#{n + 1}"
            if n > 0:
                print(f"[OpenRGBManager] Duplicate device name '{ctrl.topology.device.name}' "
                      f"→ key '{ctrl.device_key}'")

    @staticmethod
    def _detect_topology(device) -> TopologyType:
        """Several LEDs -> LINEAR (a keyboard too: it is read as plain zones, one
        colour per zone), otherwise SINGLE. MATRIX is kept only for old configs."""
        if len(device.leds) > 1:
            return TopologyType.LINEAR
        return TopologyType.SINGLE

    # ── Interface (compatible with AmbilightService) ───────────────────────────

    def _make_device_key(self, ctrl: DeviceController) -> str:
        return ctrl.device_key or (
            f"{ctrl.topology.device.name}::{ctrl.topology.topology_type.value}"
        )

    def is_effect_playing(self) -> bool:
        return False

    def get_device_led_count(self, device_key: str) -> Optional[int]:
        """Return the LED count reported by the hardware for a device_key,
        or None if no matching device is currently enrolled."""
        with self._lock:
            for ctrl in self.devices:
                if self._make_device_key(ctrl) == device_key:
                    return len(ctrl.topology.device.leds)
        return None

    def apply_direct_colors(
        self,
        device_key: str,
        colors: List[Tuple[int, int, int]],
    ) -> bool:
        """Apply RGB colors directly to a device. Thread-safe."""
        with self._lock:
            for ctrl in self.devices:
                if self._make_device_key(ctrl) == device_key:
                    try:
                        device = ctrl.topology.device
                        # Switch to direct mode if not already
                        if not getattr(device, '_direct_mode_set', False):
                            try:
                                device.set_mode('direct')
                                device._direct_mode_set = True
                            except Exception:
                                pass

                        # Reconcile color count with the actual LED count
                        # reported by the hardware. The topology config may be
                        # stale/misaligned (e.g. device reports a different LED
                        # count), so pad with black or truncate to avoid the
                        # "Number of colors doesn't match number of LEDs" error.
                        hw_led_count = len(device.leds)
                        if len(colors) != hw_led_count:
                            if len(colors) < hw_led_count:
                                colors = colors + [(0, 0, 0)] * (hw_led_count - len(colors))
                            else:
                                colors = colors[:hw_led_count]

                        device.set_colors(colors)
                        return True
                    except Exception as exc:
                        print(f"[OpenRGBManager] apply_direct_colors error ({device_key}): {exc}")
                        return False
        return False

    # ── Reconnect support ──────────────────────────────────────────────────────

    def reconnect(self, host: str, port: int, settle: bool = False) -> bool:
        """Attempt to reconnect to OpenRGB with new or same host/port.
        settle=True waits for a freshly started OpenRGB to finish detection."""
        try:
            from core.openrgb_sdk import OpenRGBClient
            new_client = OpenRGBClient(host, port)
            if settle:
                from utils.openrgb_bootstrap import wait_devices_settled
                wait_devices_settled(new_client)
            old_client, self._client = self._client, new_client
            if hasattr(old_client, "close"):
                old_client.close()
            self.devices.clear()
            self._init_devices()
            print(f"[OpenRGBManager] Reconnected to {host}:{port}")
            return True
        except Exception as exc:
            print(f"[OpenRGBManager] Reconnect failed: {exc}")
            return False
