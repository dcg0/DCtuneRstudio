"""Read-only ECU protocol profiles used by DC Tuner Studio.

These adapters deliberately expose identification and parsing primitives only.
Write/flash commands are not implemented until backup, checksum, cancellation,
and recovery workflows are validated against hardware.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryFrame:
    rpm: float
    map_kpa: float
    tps: float
    clt: float
    afr: float
    battery: float


class ProtocolAdapter:
    name = "Generic serial"
    baudrate = 115200

    def identify_command(self) -> bytes:
        return b"\x00"

    def parse_line(self, line: str) -> TelemetryFrame | None:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            return None
        try:
            values = [float(value) for value in parts[:6]]
        except ValueError:
            return None
        return TelemetryFrame(*values)

    def write_capability(self) -> bool:
        return False


class SpeeduinoAdapter(ProtocolAdapter):
    name = "Speeduino (serial read-only)"
    baudrate = 115200

    def identify_command(self) -> bytes:
        return b"SPEEDUINO?\r\n"


class MegaSquirtAdapter(ProtocolAdapter):
    name = "MegaSquirt / Microsquirt (serial read-only)"
    baudrate = 115200

    def identify_command(self) -> bytes:
        return b"\x00\x00"

    def parse_line(self, line: str) -> TelemetryFrame | None:
        # The MVP accepts a documented CSV fixture for deterministic testing.
        # Binary Megasquirt datalog decoding belongs in a versioned protocol fixture.
        return super().parse_line(line)


class Elm327Adapter(ProtocolAdapter):
    name = "ELM327 USB/Bluetooth (AT read-only)"
    baudrate = 115200

    def identify_command(self) -> bytes:
        return b"ATI\r"

    def parse_line(self, line: str) -> TelemetryFrame | None:
        # ELM327 responses are decoded into a normalized CSV frame by the transport.
        return super().parse_line(line)


PROTOCOLS = {
    "Speeduino": SpeeduinoAdapter,
    "MegaSquirt / Microsquirt": MegaSquirtAdapter,
    "ELM327": Elm327Adapter,
}
