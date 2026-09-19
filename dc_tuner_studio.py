#!/usr/bin/env python3
"""DC Tuner Studio - offline-first desktop MVP.

The application intentionally runs on Python's standard library only. Real serial
support is optional: install pyserial and select a detected port, or use the
built-in ECU simulator for safe development and demonstrations.
"""
from __future__ import annotations

import csv
import json
import math
import struct
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from ini_loader import EcuDefinition, load_definition
from platform_support import desktop_geometry, detect_runtime
from protocols import PROTOCOLS, ProtocolAdapter

APP_NAME = "DC TUNER STUDIO"
VERSION = "0.1.0"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
COLORS = {
    "bg": "#0A0A0A", "panel": "#11161A", "panel2": "#182229",
    "blue": "#00A8FF", "red": "#FF2020", "silver": "#C8C8C8",
    "green": "#00E060", "muted": "#71808A", "grid": "#26343C",
    "white": "#F5F7F8", "amber": "#F7B955",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate_horsepower(sample: dict, displacement_l: float = 2.0, ve: float = 0.85) -> float:
    """Rough airflow-based estimate; not a dyno measurement.

    Assumes a four-stroke engine, standard air density, and 0.50 lb/hp-hour
    brake-specific fuel consumption. Without displacement/torque calibration,
    this value is intentionally labeled as an estimate.
    """
    rpm = max(0.0, float(sample.get("rpm", 0)))
    map_kpa = clamp(float(sample.get("map", 0)), 0, 150)
    afr = clamp(float(sample.get("afr", 14.7)), 8, 25)
    air_kg_min = (displacement_l * rpm / 2 / 1000) * 1.225 * (map_kpa / 101.325) * ve
    air_lb_min = air_kg_min * 2.20462
    return max(0.0, air_lb_min * 60 / (afr * 0.50))


class Tooltip:
    """Small non-blocking hover note for dense tuning screens."""
    def __init__(self, widget: tk.Misc, text: str) -> None:
        self.widget, self.text = widget, text
        self.window: Optional[tk.Toplevel] = None
        self.after_id: Optional[str] = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def schedule(self, _event: tk.Event) -> None:
        self.after_id = self.widget.after(450, self.show)

    def show(self) -> None:
        if self.window or not self.widget.winfo_viewable():
            return
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.configure(background=COLORS["blue"])
        label = tk.Label(self.window, text=self.text, justify="left", wraplength=280,
                         bg=COLORS["panel2"], fg=COLORS["white"], padx=10, pady=7,
                         font=("Arial", 9))
        label.pack(padx=1, pady=1)
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.window.geometry(f"+{x}+{y}")

    def hide(self, _event: tk.Event | None = None) -> None:
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.window:
            self.window.destroy()
            self.window = None


class RoundGauge(tk.Canvas):
    """Automotive-style circular gauge for high-priority live values."""
    def __init__(self, parent: tk.Misc, title: str, unit: str, maximum: float, accent: str, redline: float | None = None) -> None:
        super().__init__(parent, width=330, height=270, bg=COLORS["panel"], highlightthickness=0)
        self.title, self.unit, self.maximum, self.accent, self.redline = title, unit, maximum, accent, redline
        self.value = 0.0
        self.bind("<Enter>", lambda _event: self.configure(cursor="crosshair"))
        self.draw()

    def set_value(self, value: float) -> None:
        self.value = clamp(float(value), 0, self.maximum)
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        cx, cy, radius = 165, 132, 108
        self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#080B0D", outline=COLORS["grid"], width=3)
        self.create_arc(cx - radius + 7, cy - radius + 7, cx + radius - 7, cy + radius - 7, start=210, extent=-240, style="arc", outline=COLORS["muted"], width=8)
        if self.redline is not None:
            start = 210 - (self.redline / self.maximum) * 240
            self.create_arc(cx - radius + 7, cy - radius + 7, cx + radius - 7, cy + radius - 7, start=start, extent=-(240 - (self.redline / self.maximum) * 240), style="arc", outline=COLORS["red"], width=8)
        for tick in range(11):
            fraction = tick / 10
            angle = math.radians(210 - fraction * 240)
            inner = radius - 17 if tick % 2 == 0 else radius - 12
            x1, y1 = cx + inner * math.cos(angle), cy - inner * math.sin(angle)
            x2, y2 = cx + (radius - 6) * math.cos(angle), cy - (radius - 6) * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=COLORS["silver"], width=2)
            if tick % 2 == 0:
                tx, ty = cx + (radius - 29) * math.cos(angle), cy - (radius - 29) * math.sin(angle)
                self.create_text(tx, ty, text=str(int(self.maximum * fraction)), fill=COLORS["silver"], font=("Arial", 8))
        angle = math.radians(210 - (self.value / self.maximum) * 240)
        nx, ny = cx + (radius - 22) * math.cos(angle), cy - (radius - 22) * math.sin(angle)
        self.create_line(cx, cy, nx, ny, fill=self.accent, width=4)
        self.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=self.accent, outline=COLORS["white"])
        self.create_text(cx, 30, text=self.title, fill=COLORS["white"], font=("Arial", 13, "bold"))
        self.create_text(cx, 192, text=f"{self.value:.0f}", fill=self.accent, font=("Arial", 30, "bold"))
        self.create_text(cx, 225, text=self.unit, fill=COLORS["muted"], font=("Arial", 11))


@dataclass
class MapData:
    name: str = "Base Map"
    rows: int = 16
    cols: int = 16
    values: list[list[float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.values:
            self.values = [[round(35 + r * 2.2 + c * 1.35 + math.sin(c / 2) * 4, 1)
                            for c in range(self.cols)] for r in range(self.rows)]

    def clone(self, name: Optional[str] = None) -> "MapData":
        return MapData(name or self.name, self.rows, self.cols, [row[:] for row in self.values])

    def to_dict(self) -> dict:
        return {"format": "DC-TUNER-MSQ", "version": 1, "name": self.name,
                "rows": self.rows, "cols": self.cols, "values": self.values}

    @classmethod
    def from_dict(cls, payload: dict) -> "MapData":
        values = payload.get("values") or []
        if not values or not isinstance(values, list):
            raise ValueError("El mapa no contiene una matriz de valores válida")
        rows = len(values)
        cols = len(values[0])
        if any(len(row) != cols for row in values):
            raise ValueError("La matriz del mapa no es rectangular")
        return cls(str(payload.get("name", "Imported Map")), rows, cols,
                   [[float(value) for value in row] for row in values])

    def save(self, path: Path) -> None:
        if path.suffix.lower() == ".bin":
            with path.open("wb") as handle:
                handle.write(b"DCTB\x01")
                handle.write(struct.pack("<HH", self.rows, self.cols))
                for row in self.values:
                    for value in row:
                        handle.write(struct.pack("<f", float(value)))
            return
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "MapData":
        if path.suffix.lower() == ".bin":
            raw = path.read_bytes()
            if raw[:5] != b"DCTB\x01":
                raise ValueError("BIN no reconocido: se esperaba un archivo DCTB de muestra")
            rows, cols = struct.unpack("<HH", raw[5:9])
            expected = 9 + rows * cols * 4
            if len(raw) != expected:
                raise ValueError("BIN incompleto o corrupto")
            values = []
            offset = 9
            for _ in range(rows):
                row = []
                for _ in range(cols):
                    row.append(round(struct.unpack("<f", raw[offset:offset + 4])[0], 3))
                    offset += 4
                values.append(row)
            return cls(path.stem, rows, cols, values)
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


class EcuTransport:
    """Safe transport abstraction with a deterministic simulator fallback."""
    def __init__(self, on_sample: Callable[[dict], None]) -> None:
        self.on_sample = on_sample
        self.protocol: ProtocolAdapter = PROTOCOLS["MegaSquirt / Microsquirt"]()
        self.connected = False
        self.simulator = False
        self.port = ""
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def set_protocol(self, protocol_name: str) -> None:
        if self.connected:
            raise RuntimeError("Desconecta antes de cambiar el protocolo")
        adapter = PROTOCOLS.get(protocol_name)
        if not adapter:
            raise ValueError(f"Protocolo no soportado: {protocol_name}")
        self.protocol = adapter()

    def available_ports(self) -> list[str]:
        ports: list[str] = []
        try:
            import serial.tools.list_ports  # type: ignore
            ports += [p.device for p in serial.tools.list_ports.comports()]
        except ImportError:
            pass
        return ports

    def connect(self, port: str) -> None:
        if not port:
            raise RuntimeError("No hay un puerto ECU real seleccionado")
        self.port = port
        try:
            import serial  # type: ignore
            self._serial = serial.Serial(port, self.protocol.baudrate, timeout=0.5)
        except ImportError as exc:
            raise RuntimeError("Instala pyserial para usar puertos USB reales") from exc
        except Exception as exc:
            raise RuntimeError(f"No se pudo abrir {port}: {exc}") from exc
        self.connected = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def disconnect(self) -> None:
        self.connected = False
        self._stop.set()
        serial_port = getattr(self, "_serial", None)
        if serial_port:
            serial_port.close()

    def _loop(self) -> None:
        while not self._stop.wait(0.25):
            sample = self._read_serial_sample()
            if sample.get("valid"):
                self.on_sample(sample)

    def _read_serial_sample(self) -> dict:
        line = self._serial.readline().decode(errors="ignore").strip()
        frame = self.protocol.parse_line(line)
        if frame is None:
            return {"valid": False, "timestamp": time.time()}
        result = {"rpm": frame.rpm, "map": frame.map_kpa, "tps": frame.tps, "speed": 0,
                  "clt": frame.clt, "iat": 0, "afr": frame.afr, "advance": 0,
                  "pulse": 0, "battery": frame.battery, "valid": True}
        result["timestamp"] = time.time()
        return result


class SurfaceCanvas(tk.Canvas):
    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        super().__init__(parent, background=COLORS["panel"], highlightthickness=0, **kwargs)
        self.map_data: Optional[MapData] = None
        self.mode = "3d"
        self.bind("<Configure>", lambda _event: self.draw())

    def set_map(self, map_data: MapData, mode: str = "3d") -> None:
        self.map_data, self.mode = map_data, mode
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        if not self.map_data:
            return
        if self.mode == "2d":
            self._draw_2d()
        else:
            self._draw_3d()

    def _color(self, value: float, low: float, high: float) -> str:
        ratio = clamp((value - low) / max(0.01, high - low), 0, 1)
        red = int(30 + 220 * ratio)
        green = int(170 - 125 * ratio)
        return f"#{red:02x}{green:02x}55"

    def _draw_2d(self) -> None:
        data = self.map_data
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        left, top, right, bottom = 55, 22, width - 20, height - 35
        low, high = min(map(min, data.values)), max(map(max, data.values))
        for r, row in enumerate(data.values):
            points = []
            for c, value in enumerate(row):
                x = left + (right - left) * c / max(1, data.cols - 1)
                y = bottom - (bottom - top) * (value - low) / max(0.01, high - low)
                points.extend((x, y))
            if len(points) >= 4:
                self.create_line(*points, fill=COLORS["blue"], width=2, smooth=True)
        for tick in range(5):
            y = top + (bottom - top) * tick / 4
            self.create_line(left, y, right, y, fill=COLORS["grid"])
        self.create_text(12, top, text=f"{high:.1f}", fill=COLORS["silver"], anchor="w")
        self.create_text(12, bottom, text=f"{low:.1f}", fill=COLORS["silver"], anchor="w")
        self.create_text(width / 2, height - 10, text="Celdas del mapa →", fill=COLORS["muted"])

    def _draw_3d(self) -> None:
        data = self.map_data
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        ox, oy = width * .5, height * .72
        sx, sy, sz = width / max(20, data.cols * 1.8), height / max(20, data.rows * 2.2), height * .42
        low, high = min(map(min, data.values)), max(map(max, data.values))
        for r in range(data.rows - 1, -1, -1):
            for c in range(data.cols):
                value = data.values[r][c]
                z = (value - low) / max(.01, high - low)
                x = ox + (c - r) * sx
                y = oy + (c + r) * sy * .35 - z * sz
                x2 = x + sx
                y2 = y + sy * .35
                x3 = x2 - sx
                y3 = y2 + sy * .35
                self.create_polygon(x, y, x2, y2, x3, y3, fill=self._color(value, low, high), outline=COLORS["grid"])
        self.create_text(18, 18, text=f"MIN {low:.1f}   MAX {high:.1f}", fill=COLORS["silver"], anchor="nw")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._show_splash()
        self.title(f"{APP_NAME}  |  v{VERSION}")
        self.runtime = detect_runtime()
        self.geometry(desktop_geometry(self))
        self.minsize(1100, 720)
        self.tk.call("tk", "scaling", max(1.0, self.winfo_fpixels("1i") / 72.0))
        self.configure(background=COLORS["bg"])
        self.map_a = MapData("Base Map")
        self.map_b = self.map_a.clone("Comparison Map")
        self.samples: list[dict] = []
        self.transport = EcuTransport(self.receive_sample)
        self.status_var = tk.StringVar(value=f"DESCONECTADO · {self.runtime.label}")
        self.port_var = tk.StringVar(value="")
        self.protocol_var = tk.StringVar(value="MegaSquirt / Microsquirt")
        self.hover_var = tk.StringVar(value="Pasa el ratón sobre un dato para ver qué significa")
        self.displacement_var = tk.StringVar(value="2.0")
        self.ve_var = tk.StringVar(value="85")
        self.definition: Optional[EcuDefinition] = None
        self.view_var = tk.StringVar(value="3d")
        self._configure_style()
        self._build_menu()
        self._build_header()
        self._build_body()
        self.refresh_ports()
        self.after(400, self.refresh_live_ui)

    def _show_splash(self) -> None:
        """Show the supplied cover art while the desktop workspace initializes."""
        self.withdraw()
        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.configure(background=COLORS["bg"])
        splash.geometry("1080x505")
        splash.update_idletasks()
        x = max(0, (splash.winfo_screenwidth() - 1080) // 2)
        y = max(0, (splash.winfo_screenheight() - 505) // 2)
        splash.geometry(f"1080x505+{x}+{y}")
        cover_path = ASSET_DIR / "dc-tuner-cover.gif"
        if cover_path.exists():
            self._splash_image = tk.PhotoImage(file=str(cover_path))
            tk.Label(splash, image=self._splash_image, bg=COLORS["bg"]).pack(fill="both", expand=True)
        else:
            tk.Label(splash, text=APP_NAME, font=("Arial", 38, "bold"), fg=COLORS["blue"], bg=COLORS["bg"]).pack(expand=True)
        splash.update()
        self.after(1400, lambda: (splash.destroy(), self.deiconify()))

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["panel"], foreground=COLORS["silver"], padding=(18, 8))
        style.map("TNotebook.Tab", background=[("selected", COLORS["blue"])], foreground=[("selected", "white")])
        style.configure("TButton", background=COLORS["panel2"], foreground=COLORS["white"], borderwidth=0, padding=8)
        style.map("TButton", background=[("active", COLORS["blue"])])
        style.configure("TCombobox", fieldbackground=COLORS["panel2"], background=COLORS["panel2"], foreground=COLORS["white"])
        style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["silver"], rowheight=26)
        style.configure("Treeview.Heading", background=COLORS["panel2"], foreground=COLORS["blue"])

    def _build_menu(self) -> None:
        menu = tk.Menu(self, tearoff=False, background=COLORS["panel"], foreground=COLORS["white"])
        file_menu = tk.Menu(menu, tearoff=False, background=COLORS["panel"], foreground=COLORS["white"])
        file_menu.add_command(label="Abrir mapa…", command=self.open_map)
        file_menu.add_command(label="Cargar definición ECU (.ini)…", command=self.load_definition)
        file_menu.add_command(label="Guardar mapa…", command=self.save_map)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar log CSV…", command=self.export_csv)
        file_menu.add_command(label="Exportar resumen PDF…", command=self.export_pdf)
        file_menu.add_separator(); file_menu.add_command(label="Salir", command=self.destroy)
        menu.add_cascade(label="Archivo", menu=file_menu)
        menu.add_command(label="Conexión", command=self.toggle_connection)
        menu.add_command(label="Manual y funciones", command=lambda: self.notebook.select(self.help_tab))
        menu.add_command(label="Ayuda", command=self.show_about)
        self.config(menu=menu)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["bg"], height=82)
        header.pack(fill="x", padx=22, pady=(16, 8)); header.pack_propagate(False)
        logo = tk.Frame(header, bg=COLORS["bg"]); logo.pack(side="left")
        tk.Label(logo, text="DC", font=("Arial", 34, "bold"), fg=COLORS["blue"], bg=COLORS["bg"]).pack(side="left")
        tk.Label(logo, text=" TUNER", font=("Arial", 27, "bold"), fg=COLORS["white"], bg=COLORS["bg"]).pack(side="left")
        tk.Label(logo, text=" STUDIO", font=("Arial", 17, "bold"), fg=COLORS["red"], bg=COLORS["bg"]).pack(side="left", pady=(17, 0))
        right = tk.Frame(header, bg=COLORS["bg"]); right.pack(side="right", fill="y")
        self.connection_label = tk.Label(right, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Arial", 10, "bold")); self.connection_label.pack(anchor="e")
        controls = tk.Frame(right, bg=COLORS["bg"]); controls.pack(anchor="e", pady=8)
        self.protocol_combo = ttk.Combobox(controls, textvariable=self.protocol_var, width=28, state="readonly", values=list(PROTOCOLS)); self.protocol_combo.pack(side="left", padx=5)
        self.port_combo = ttk.Combobox(controls, textvariable=self.port_var, width=18, state="readonly"); self.port_combo.pack(side="left", padx=5)
        Tooltip(self.protocol_combo, "Perfil de comunicación. Selecciona el firmware antes de conectar.")
        Tooltip(self.port_combo, "Puerto USB/Bluetooth real detectado. Sin ECU conectada no se muestran valores.")
        refresh_button = ttk.Button(controls, text="Actualizar", command=self.refresh_ports); refresh_button.pack(side="left", padx=3)
        Tooltip(refresh_button, "Vuelve a buscar puertos serie conectados.")
        self.connect_btn = ttk.Button(controls, text="Conectar", command=self.toggle_connection); self.connect_btn.pack(side="left", padx=3)
        Tooltip(self.connect_btn, "Conecta en modo lectura. Las escrituras ECU están bloqueadas en esta versión.")

    def _build_body(self) -> None:
        self.notebook = ttk.Notebook(self); self.notebook.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.live_tab = tk.Frame(self.notebook, bg=COLORS["bg"]); self.map_tab = tk.Frame(self.notebook, bg=COLORS["bg"]); self.log_tab = tk.Frame(self.notebook, bg=COLORS["bg"]); self.compare_tab = tk.Frame(self.notebook, bg=COLORS["bg"]); self.help_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        for tab, label in ((self.live_tab, "PANEL EN VIVO"), (self.map_tab, "EDITOR DE MAPAS"), (self.log_tab, "REGISTRO Y ANÁLISIS"), (self.compare_tab, "COMPARAR MAPAS"), (self.help_tab, "MANUAL Y FUNCIONES")):
            self.notebook.add(tab, text=label)
        self._build_live(); self._build_map(); self._build_log(); self._build_compare(); self._build_help()
        footer = tk.Frame(self, bg=COLORS["panel2"], height=28); footer.pack(fill="x", side="bottom"); footer.pack_propagate(False)
        tk.Label(footer, text="USB / ELM327 · MS1 / MS2 / MS3 · Microsquirt", bg=COLORS["panel2"], fg=COLORS["muted"]).pack(side="left", padx=14)
        self.footer_var = tk.StringVar(value=f"{self.runtime.label}   |   Puerto: sin ECU   |   esperando hardware real")
        tk.Label(footer, textvariable=self.footer_var, bg=COLORS["panel2"], fg=COLORS["silver"]).pack(side="right", padx=14)
        tk.Label(footer, textvariable=self.hover_var, bg=COLORS["panel2"], fg=COLORS["blue"], anchor="w").pack(side="left", padx=14, fill="x", expand=True)

    def _build_help(self) -> None:
        self.help_tab.rowconfigure(1, weight=1); self.help_tab.columnconfigure(0, weight=1)
        tk.Label(self.help_tab, text="MANUAL INTEGRADO · MODELO TUNERSTUDIO MS", bg=COLORS["bg"], fg=COLORS["blue"], font=("Arial", 15, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 5))
        manual = tk.Text(self.help_tab, wrap="word", bg=COLORS["panel"], fg=COLORS["silver"], insertbackground=COLORS["white"], relief="flat", padx=18, pady=16)
        manual.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        manual.insert("1.0", """DC TUNER STUDIO
=================

Este manual resume el modelo de trabajo documentado públicamente para TunerStudio MS y explica cómo se incorpora en DC TUNER STUDIO.

PANEL EN VIVO Y DASHBOARDS
• Vistas por pestañas, gauges seleccionables y pantalla completa.
• Próxima fase: diseñador drag-and-drop, dashboards guardables y canales runtime desde archivos de definición ECU.

MAPAS Y AJUSTE
• Tablas 2D/3D, comparación de mapas, targeting de celdas y edición offline.
• Próxima fase: VE Analyze con filtros, heatmap, hit counts, authority limits y propuesta de cambios.
• Los cambios deberán guardarse como restore point antes de escribir.

REGISTRO Y DIAGNÓSTICO
• Registro en vivo, perfiles de canales, condiciones de inicio/parada y reproducción.
• Loggers de trigger/tooth/composite/sync dependen del firmware y de su definición.
• DTC no es universal: se implementará por adaptador ECU, nunca como comando genérico.

CONEXIONES
• Speeduino, MegaSquirt/Microsquirt y ELM327 tienen perfiles separados.
• Solo se muestran valores recibidos de hardware real y tramas válidas.
• Verifica firmware, puerto y valores antes de ajustar.
• No hay escritura, burn ni prueba de actuadores automática en esta versión.

SEGURIDAD
Antes de habilitar escritura: backup, checksum, confirmación de dispositivo, cancelación, registro de bytes y recuperación.
Para pruebas de actuadores, sigue la documentación del firmware y desconecta el ECU del vehículo cuando corresponda.

Documentación ampliada: docs/TUNERSTUDIO_COMPATIBILITY.md
Fuentes: EFI Analytics TunerStudio, documentación de definiciones ECU y wiki de Speeduino.
""")
        manual.configure(state="disabled")

    def _card(self, parent: tk.Misc, title: str, row: int, col: int) -> tk.LabelFrame:
        card = tk.LabelFrame(parent, text=title, bg=COLORS["panel"], fg=COLORS["blue"], font=("Arial", 10, "bold"), padx=12, pady=10, bd=0)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        return card

    def _build_live(self) -> None:
        self.live_tab.columnconfigure((0, 1, 2), weight=1)
        self.live_tab.rowconfigure(4, weight=1)
        self.metric_labels: dict[str, tk.Label] = {}
        self.hp_value_label: Optional[tk.Label] = None
        self.tacho_gauge: Optional[RoundGauge] = None
        self.speed_gauge: Optional[RoundGauge] = None
        metrics = (("RPM", "rpm", "rpm", "#00A8FF", "Revoluciones del motor", "Vigila el ralentí y cambios bruscos."), ("MAP", "map", "kPa", "#00E060", "Presión absoluta del múltiple", "Indica la carga y el vacío del motor."), ("TPS", "tps", "%", "#F7B955", "Posición de mariposa", "Compárala con MAP y RPM al acelerar."), ("CLT", "clt", "°C", "#FF2020", "Temperatura de refrigerante", "Debe subir gradualmente; vigila sobrecalentamiento."), ("IAT", "iat", "°C", "#FF8A3D", "Temperatura de admisión", "Ayuda a interpretar densidad y compensación de combustible."), ("AFR", "afr", "AFR", "#C8C8C8", "Relación aire/combustible", "Compara con el objetivo y la carga del motor."), ("Avance", "advance", "°", "#B780FF", "Avance de encendido", "Observa estabilidad y cambios bajo carga."), ("Pulso iny.", "pulse", "ms", "#FF5CC8", "Tiempo de inyección", "Útil para detectar saturación o cambios de carga."), ("Batería", "battery", "V", "#38D6FF", "Voltaje de alimentación", "Una caída puede afectar la comunicación ECU."))
        for index, (title, key, unit, color, description, note) in enumerate(metrics):
            card = self._card(self.live_tab, title, index // 3 + 1, index % 3)
            card.configure(labelanchor="nw")
            row = tk.Frame(card, bg=COLORS["panel"]); row.pack(fill="x", pady=(3, 0))
            label = tk.Label(row, text="—", font=("Arial", 24, "bold"), bg=COLORS["panel"], fg=color); label.pack(side="left")
            tk.Label(row, text=f" {unit}", font=("Arial", 11, "bold"), bg=COLORS["panel"], fg=COLORS["muted"]).pack(side="left", pady=(9, 0))
            tk.Label(card, text=description, font=("Arial", 8), bg=COLORS["panel"], fg=COLORS["silver"], anchor="w").pack(fill="x", pady=(2, 5))
            Tooltip(card, note); Tooltip(label, note)
            self.metric_labels[key] = label
        gauge_card = self._card(self.live_tab, "INSTRUMENTOS PRINCIPALES", 0, 0); gauge_card.grid(columnspan=3, sticky="nsew")
        self.gauge_frame = tk.Frame(gauge_card, bg=COLORS["panel"]); self.gauge_frame.pack(fill="both", expand=True, pady=(0, 2))
        self.tacho_gauge = RoundGauge(self.gauge_frame, "TACÓMETRO", "RPM", 8000, COLORS["blue"], 6500); self.tacho_gauge.pack(side="left", expand=True, padx=24)
        self.speed_gauge = RoundGauge(self.gauge_frame, "VELOCÍMETRO", "km/h", 240, COLORS["green"]); self.speed_gauge.pack(side="left", expand=True, padx=24)
        Tooltip(self.tacho_gauge, "Tacómetro: RPM del motor. Zona roja desde 6.500 RPM en esta vista de demostración.")
        Tooltip(self.speed_gauge, "Velocímetro: velocidad estimada en km/h. La señal real depende del firmware y sensor disponible.")
        graph_card = self._card(self.live_tab, "TELEMETRÍA EN TIEMPO REAL · AFR / MAP", 4, 0); graph_card.grid(columnspan=2, sticky="nsew")
        self.rate_var = tk.StringVar(value="Sin muestras ECU válidas")
        tk.Label(graph_card, textvariable=self.rate_var, bg=COLORS["panel"], fg=COLORS["muted"], font=("Arial", 8)).pack(anchor="e", padx=8)
        self.live_canvas = tk.Canvas(graph_card, height=145, bg=COLORS["panel"], highlightthickness=0); self.live_canvas.pack(fill="both", expand=True)
        quick = self._card(self.live_tab, "ESTADO Y CONSEJOS DE AJUSTE", 4, 2)
        hp_box = tk.Frame(quick, bg=COLORS["panel2"], padx=10, pady=7); hp_box.pack(fill="x", pady=(0, 8))
        tk.Label(hp_box, text="POTENCIA ESTIMADA · ACTIVA", bg=COLORS["panel2"], fg=COLORS["muted"], font=("Arial", 9, "bold")).pack(anchor="w")
        self.hp_value_label = tk.Label(hp_box, text="— CV", bg=COLORS["panel2"], fg="#B780FF", font=("Arial", 24, "bold")); self.hp_value_label.pack(anchor="w")
        hp_note = tk.Label(hp_box, text="ESTIMACIÓN · no es medición de banco", bg=COLORS["panel2"], fg=COLORS["amber"], font=("Arial", 8, "bold")); hp_note.pack(anchor="w")
        assumptions = tk.Frame(hp_box, bg=COLORS["panel2"]); assumptions.pack(fill="x", pady=(5, 0))
        tk.Label(assumptions, text="Cilindrada L", bg=COLORS["panel2"], fg=COLORS["muted"], font=("Arial", 8)).pack(side="left")
        ttk.Entry(assumptions, textvariable=self.displacement_var, width=5).pack(side="left", padx=(4, 10))
        tk.Label(assumptions, text="VE %", bg=COLORS["panel2"], fg=COLORS["muted"], font=("Arial", 8)).pack(side="left")
        ttk.Entry(assumptions, textvariable=self.ve_var, width=5).pack(side="left", padx=4)
        tk.Label(hp_box, text="RPM + MAP + AFR · fórmula de flujo de aire", bg=COLORS["panel2"], fg=COLORS["muted"], font=("Arial", 7)).pack(anchor="w")
        Tooltip(hp_box, "Estimación orientativa usando RPM, MAP y AFR. Supuestos visibles: motor 2,0 L y 85% VE. No sustituye un dinamómetro.")
        self.quick_status = tk.Text(quick, height=12, width=32, bg=COLORS["panel"], fg=COLORS["silver"], relief="flat", state="disabled")
        self.quick_status.pack(fill="both", expand=True); self._set_quick("Sin ECU conectada.\n\nNo se muestran datos inventados.\n\nConsejos rápidos:\n• Cambia una zona cada vez.\n• Compara AFR con MAP y RPM.\n• Guarda una copia antes de ajustar.\n• Verifica CLT, IAT y batería.\n\nModo lectura: no se envía escritura ECU automáticamente.")

    def _build_map(self) -> None:
        self.map_tab.columnconfigure(0, weight=1); self.map_tab.rowconfigure(0, weight=1)
        self.surface = SurfaceCanvas(self.map_tab); self.surface.grid(row=0, column=0, sticky="nsew", padx=8, pady=8); self.surface.set_map(self.map_a); self.surface.bind("<Motion>", self.on_map_hover, add="+")
        side = tk.Frame(self.map_tab, bg=COLORS["panel"], width=240); side.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8); side.grid_propagate(False)
        tk.Label(side, text="CONTROLES DEL MAPA", bg=COLORS["panel"], fg=COLORS["blue"], font=("Arial", 11, "bold")).pack(anchor="w", padx=14, pady=14)
        ttk.Button(side, text="Abrir .MSQ / .BIN", command=self.open_map).pack(fill="x", padx=14, pady=5)
        ttk.Button(side, text="Guardar mapa", command=self.save_map).pack(fill="x", padx=14, pady=5)
        ttk.Button(side, text="Duplicar mapa", command=self.duplicate_map).pack(fill="x", padx=14, pady=5)
        ttk.Separator(side).pack(fill="x", padx=14, pady=14)
        tk.Label(side, text="Vista", bg=COLORS["panel"], fg=COLORS["silver"]).pack(anchor="w", padx=14)
        for label, mode in (("Superficie 3D", "3d"), ("Curvas 2D", "2d")):
            ttk.Radiobutton(side, text=label, value=mode, variable=self.view_var, command=lambda: self.surface.set_map(self.map_a, self.view_var.get())).pack(anchor="w", padx=14, pady=5)
        ttk.Separator(side).pack(fill="x", padx=14, pady=14)
        tk.Label(side, text="Mapa activo", bg=COLORS["panel"], fg=COLORS["muted"]).pack(anchor="w", padx=14)
        self.map_name_var = tk.StringVar(value=self.map_a.name)
        tk.Label(side, textvariable=self.map_name_var, bg=COLORS["panel"], fg=COLORS["white"], wraplength=200).pack(anchor="w", padx=14, pady=5)
        help_label = tk.Label(side, text="MSQ compatible / BIN DCTB", bg=COLORS["panel"], fg=COLORS["muted"]); help_label.pack(anchor="w", padx=14, pady=4)
        Tooltip(help_label, "Pasa el ratón sobre la superficie para ver fila, columna, valor y una nota de ajuste.")

    def _build_log(self) -> None:
        self.log_tab.rowconfigure(0, weight=1); self.log_tab.columnconfigure(0, weight=1)
        self.log_tree = ttk.Treeview(self.log_tab, columns=("time", "rpm", "map", "tps", "clt", "afr", "battery"), show="headings")
        for key, title in (("time", "Hora"), ("rpm", "RPM"), ("map", "MAP"), ("tps", "TPS"), ("clt", "CLT"), ("afr", "AFR"), ("battery", "Voltaje")):
            self.log_tree.heading(key, text=title); self.log_tree.column(key, width=105, anchor="center")
        self.log_tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        controls = tk.Frame(self.log_tab, bg=COLORS["bg"]); controls.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        ttk.Button(controls, text="Exportar CSV", command=self.export_csv).pack(side="left", padx=4)
        ttk.Button(controls, text="Exportar PDF", command=self.export_pdf).pack(side="left", padx=4)
        ttk.Button(controls, text="Limpiar registro", command=self.clear_log).pack(side="left", padx=4)
        self.log_summary = tk.Label(controls, text="0 muestras · espera conexión", bg=COLORS["bg"], fg=COLORS["muted"]); self.log_summary.pack(side="right", padx=8)

    def _build_compare(self) -> None:
        self.compare_tab.columnconfigure(0, weight=1); self.compare_tab.columnconfigure(1, weight=1); self.compare_tab.rowconfigure(1, weight=1)
        bar = tk.Frame(self.compare_tab, bg=COLORS["bg"]); bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Button(bar, text="Cargar mapa B", command=self.load_map_b).pack(side="left", padx=4)
        ttk.Button(bar, text="Comparar diferencias", command=self.compare_maps).pack(side="left", padx=4)
        self.diff_summary = tk.Label(bar, text="Carga dos mapas para ver diferencias", bg=COLORS["bg"], fg=COLORS["muted"]); self.diff_summary.pack(side="right", padx=8)
        self.diff_tree = ttk.Treeview(self.compare_tab, columns=("cell", "a", "b", "diff"), show="headings")
        for key, title in (("cell", "Celda"), ("a", "Mapa A"), ("b", "Mapa B"), ("diff", "Diferencia")):
            self.diff_tree.heading(key, text=title); self.diff_tree.column(key, width=170, anchor="center")
        self.diff_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)

    def _set_quick(self, text: str) -> None:
        self.quick_status.configure(state="normal"); self.quick_status.delete("1.0", "end"); self.quick_status.insert("1.0", text); self.quick_status.configure(state="disabled")

    def on_map_hover(self, event: tk.Event) -> None:
        if not self.map_a.values:
            return
        width = max(1, self.surface.winfo_width()); height = max(1, self.surface.winfo_height())
        col = min(self.map_a.cols - 1, max(0, int((event.x / width) * self.map_a.cols)))
        row = min(self.map_a.rows - 1, max(0, int((event.y / height) * self.map_a.rows)))
        value = self.map_a.values[row][col]
        self.hover_var.set(f"Celda R{row + 1}/C{col + 1} · valor {value:.2f} · Ajuste: cambia poco, compara AFR/MAP y guarda una copia antes de escribir")

    def refresh_ports(self) -> None:
        ports = self.transport.available_ports(); self.port_combo["values"] = ports
        if self.port_var.get() not in ports: self.port_var.set(ports[0] if ports else "")

    def toggle_connection(self) -> None:
        if self.transport.connected:
            self.transport.disconnect(); self.status_var.set("DESCONECTADO · modo seguro"); self.connect_btn.configure(text="Conectar"); self.connection_label.configure(fg=COLORS["muted"])
            self._set_quick("Conexión cerrada.\n\nLos datos registrados permanecen disponibles para exportación.\n\nNo se generan datos sintéticos.")
            return
        try:
            self.transport.set_protocol(self.protocol_var.get())
            self.transport.connect(self.port_var.get())
            self.status_var.set(f"CONECTADO · {self.port_var.get()}"); self.connect_btn.configure(text="Desconectar"); self.connection_label.configure(fg=COLORS["green"])
            self.footer_var.set(f"{self.protocol_var.get()}   |   {self.transport.protocol.baudrate} baud   |   ECU: hardware real")
        except RuntimeError as exc:
            messagebox.showerror("Conexión no disponible", str(exc))

    def receive_sample(self, sample: dict) -> None:
        self.samples.append(sample)
        if len(self.samples) > 2000: self.samples.pop(0)

    def refresh_live_ui(self) -> None:
        if self.samples:
            sample = self.samples[-1]
            for key, label in self.metric_labels.items(): label.configure(text=str(sample.get(key, "—")))
            if self.hp_value_label:
                try:
                    displacement = float(self.displacement_var.get())
                    ve = float(self.ve_var.get()) / 100
                    estimate = estimate_horsepower(sample, displacement, ve) if displacement > 0 and 0 < ve <= 2 else None
                except ValueError:
                    estimate = None
                self.hp_value_label.configure(text=f"{estimate:.0f} CV" if estimate is not None else "— CV")
            if self.tacho_gauge: self.tacho_gauge.set_value(sample.get("rpm", 0))
            if self.speed_gauge: self.speed_gauge.set_value(sample.get("speed", 0))
            if len(self.log_tree.get_children()) < len(self.samples):
                stamp = time.strftime("%H:%M:%S", time.localtime(sample["timestamp"]))
                values = (stamp, sample["rpm"], sample["map"], sample["tps"], sample["clt"], sample["afr"], sample["battery"])
                self.log_tree.insert("", "end", values=values)
                children = self.log_tree.get_children()
                if len(children) > 120: self.log_tree.delete(children[0])
            self.log_summary.configure(text=f"{len(self.samples)} muestras · registro activo")
            self._draw_live_graph()
        self.after(400, self.refresh_live_ui)

    def _draw_live_graph(self) -> None:
        canvas = self.live_canvas; canvas.delete("all"); width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        recent = [sample for sample in self.samples[-100:] if math.isfinite(float(sample.get("timestamp", 0)))]
        if len(recent) < 2:
            self.rate_var.set("Sin frecuencia: se necesitan 2 muestras ECU válidas")
            canvas.create_text(width / 2, height / 2, text="ESPERANDO DATOS REALES DE LA ECU", fill=COLORS["muted"], font=("Arial", 11, "bold"))
            return
        elapsed = recent[-1]["timestamp"] - recent[0]["timestamp"]
        hz = (len(recent) - 1) / elapsed if elapsed > 0 else 0
        self.rate_var.set(f"Frecuencia real de llegada: {hz:.2f} Hz · {len(recent)} muestras válidas")
        for y in range(4):
            yy = 20 + (height - 40) * y / 3; canvas.create_line(35, yy, width - 12, yy, fill=COLORS["grid"])
        for key, color, low, high in (("rpm", COLORS["blue"], 500, 2500), ("afr", COLORS["red"], 10, 18), ("map", COLORS["green"], 20, 70)):
            points = []
            for i, sample in enumerate(recent):
                x = 35 + (width - 50) * i / max(1, len(recent) - 1); ratio = clamp((sample[key] - low) / (high - low), 0, 1); y = height - 20 - ratio * (height - 40); points.extend((x, y))
            canvas.create_line(*points, fill=color, width=2, smooth=True)
        canvas.create_text(42, 10, text="RPM", fill=COLORS["blue"], anchor="w"); canvas.create_text(85, 10, text="AFR", fill=COLORS["red"], anchor="w"); canvas.create_text(125, 10, text="MAP", fill=COLORS["green"], anchor="w")

    def open_map(self) -> None:
        path = filedialog.askopenfilename(filetypes=(("Mapas MSQ/BIN", "*.msq *.MSQ *.bin *.BIN"), ("Todos", "*.*")))
        if not path: return
        try:
            self.map_a = MapData.load(Path(path)); self.map_name_var.set(self.map_a.name); self.surface.set_map(self.map_a, self.view_var.get()); self.notebook.select(self.map_tab)
        except (ValueError, OSError, json.JSONDecodeError) as exc: messagebox.showerror("Mapa no válido", str(exc))

    def load_definition(self) -> None:
        path = filedialog.askopenfilename(filetypes=(("Definición TunerStudio", "*.ini"), ("Todos", "*.*")))
        if not path:
            return
        try:
            self.definition = load_definition(Path(path))
            signature = self.definition.signature or "firma no declarada"
            version = self.definition.version or "versión no declarada"
            self.status_var.set(f"DEFINICIÓN CARGADA · {signature}")
            self.hover_var.set(f"Firmware: {signature} · versión: {version} · INI spec {self.definition.ini_spec_version or 'n/d'}")
            self._set_quick(f"Definición ECU cargada.\n\nFirma: {signature}\nVersión: {version}\nSecciones: {len(self.definition.sections)}\n\nLa definición se usa para identificar el firmware; el transporte continúa en modo lectura.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Definición no válida", str(exc))

    def save_map(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".msq", filetypes=(("DC Tuner MSQ", "*.msq"), ("DC Tuner BIN", "*.bin")))
        if path:
            try: self.map_a.save(Path(path)); self.status_var.set(f"MAPA GUARDADO · {Path(path).name}")
            except OSError as exc: messagebox.showerror("No se pudo guardar", str(exc))

    def duplicate_map(self) -> None:
        self.map_b = self.map_a.clone("Comparison Map"); self.diff_summary.configure(text="Mapa A duplicado como mapa B"); self.notebook.select(self.compare_tab)

    def load_map_b(self) -> None:
        path = filedialog.askopenfilename(filetypes=(("Mapas MSQ/BIN", "*.msq *.MSQ *.bin *.BIN"), ("Todos", "*.*")))
        if path:
            try: self.map_b = MapData.load(Path(path)); self.diff_summary.configure(text=f"Mapa B: {self.map_b.name}")
            except (ValueError, OSError, json.JSONDecodeError) as exc: messagebox.showerror("Mapa no válido", str(exc))

    def compare_maps(self) -> None:
        self.diff_tree.delete(*self.diff_tree.get_children()); count = 0; maximum = 0.0
        rows, cols = min(self.map_a.rows, self.map_b.rows), min(self.map_a.cols, self.map_b.cols)
        for r in range(rows):
            for c in range(cols):
                diff = self.map_b.values[r][c] - self.map_a.values[r][c]; maximum = max(maximum, abs(diff))
                if abs(diff) >= .01:
                    self.diff_tree.insert("", "end", values=(f"R{r + 1} / C{c + 1}", f"{self.map_a.values[r][c]:.2f}", f"{self.map_b.values[r][c]:.2f}", f"{diff:+.2f}")); count += 1
        self.diff_summary.configure(text=f"{count} celdas diferentes · máximo {maximum:.2f}")

    def export_csv(self) -> None:
        if not self.samples: messagebox.showinfo("Sin datos", "Conecta el simulador o una ECU para registrar datos."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV", "*.csv"),))
        if not path: return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=("timestamp", "rpm", "map", "tps", "clt", "afr", "battery")); writer.writeheader(); writer.writerows(self.samples)
        self.status_var.set(f"CSV EXPORTADO · {Path(path).name}")

    def export_pdf(self) -> None:
        if not self.samples: messagebox.showinfo("Sin datos", "No hay muestras para exportar."); return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=(("PDF", "*.pdf"),))
        if not path: return
        values = self.samples[-1]; lines = [APP_NAME, f"Informe de telemetría · {time.strftime('%Y-%m-%d %H:%M')}", "", f"Muestras: {len(self.samples)}", "", "Última lectura:"]
        lines += [f"  {key.upper()}: {value}" for key, value in values.items() if key != "timestamp"]
        lines += ["", "Exportación generada offline por DC Tuner Studio."]
        self._write_simple_pdf(Path(path), lines); self.status_var.set(f"PDF EXPORTADO · {Path(path).name}")

    def _write_simple_pdf(self, path: Path, lines: list[str]) -> None:
        content = ["BT", "/F1 16 Tf", "50 760 Td"]
        for i, line in enumerate(lines):
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if i: content.append("0 -22 Td")
            content.append(f"({safe}) Tj")
        content.append("ET"); stream = "\n".join(content).encode("latin-1", errors="replace")
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)]
        pdf = bytearray(b"%PDF-1.4\n%")
        offsets = [0]
        for idx, obj in enumerate(objects, 1): offsets.append(len(pdf)); pdf.extend(f"\n{idx} 0 obj\n".encode()); pdf.extend(obj); pdf.extend(b"\nendobj\n")
        xref = len(pdf); pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()); pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])); pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()); path.write_bytes(pdf)

    def clear_log(self) -> None:
        self.samples.clear(); self.log_tree.delete(*self.log_tree.get_children()); self.log_summary.configure(text="0 muestras · registro vacío")

    def show_about(self) -> None:
        messagebox.showinfo(APP_NAME, f"{APP_NAME} v{VERSION}\n\nTaller profesional de diagnóstico y calibración.\nOffline-first · código libre · DCG0")


if __name__ == "__main__":
    App().mainloop()
