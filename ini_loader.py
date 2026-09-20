"""Minimal, safe reader for TunerStudio-style ECU definition metadata.

This does not execute INI expressions or pretend to implement the full INI
specification. It extracts sections and scalar key/value metadata so a project
can identify firmware and display capabilities before a protocol adapter is
selected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class EcuDefinition:
    path: str
    sections: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def signature(self) -> str:
        return self.sections.get("MegaTune", {}).get("signature", "").strip('"')

    @property
    def version(self) -> str:
        values = self.sections.get("MegaTune", {})
        return values.get("versionInfo", values.get("MTversion", "")).strip('"')

    @property
    def ini_spec_version(self) -> str:
        return self.sections.get("TunerStudio", {}).get("iniSpecVersion", "").strip('"')

    def has_section(self, name: str) -> bool:
        return name in self.sections


def load_definition(path: Path) -> EcuDefinition:
    current = ""
    sections: dict[str, dict[str, str]] = {}
    section_pattern = re.compile(r"^\s*\[([^]]+)\]")
    key_pattern = re.compile(r"^\s*([A-Za-z_][\w.-]*)\s*=\s*(.*?)\s*(?:;.*)?$")
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith((";", "#")):
            continue
        section_match = section_pattern.match(line)
        if section_match:
            current = section_match.group(1).strip()
            sections.setdefault(current, {})
            continue
        key_match = key_pattern.match(line)
        if key_match and current:
            sections[current][key_match.group(1)] = key_match.group(2).strip()
    if not sections:
        raise ValueError("No se encontraron secciones de definición ECU")
    return EcuDefinition(str(path), sections)
