"""Native desktop runtime checks for the supported 64-bit PC targets."""
from __future__ import annotations

import platform
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimePlatform:
    system: str
    machine: str
    bits: int

    @property
    def supported(self) -> bool:
        machine = self.machine.lower()
        return self.bits == 64 and machine in {"x86_64", "amd64"}

    @property
    def label(self) -> str:
        system = "Windows" if self.system == "Windows" else "Linux" if self.system == "Linux" else self.system
        return f"{system} x86_64 · 64 bits" if self.supported else f"{self.system} {self.machine} · {self.bits} bits"


def detect_runtime() -> RuntimePlatform:
    return RuntimePlatform(platform.system(), platform.machine(), 64 if sys.maxsize > 2**32 else 32)


def desktop_geometry(root) -> str:
    """Choose a native, resizable PC window without assuming 1280x800."""
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    target_width = min(1600, max(1100, int(width * 0.90)))
    target_height = min(1000, max(720, int(height * 0.86)))
    return f"{target_width}x{target_height}"
