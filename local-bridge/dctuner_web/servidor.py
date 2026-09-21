#!/usr/bin/env python3
"""DCtuneRstudio: backend web local multiplataforma, solo ECU real.

El proceso no necesita internet. Cuando existe pyserial lee una ECU por
/dev/ttyUSB*, /dev/ttyACM* o COM*. Sin una ECU conectada no genera telemetría,
no simula valores y bloquea los comandos dirigidos al vehículo.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import re
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from flask import Flask, Response, jsonify, request, send_from_directory

try:
    import serial
    from serial import SerialException
except ImportError:  # El instalador ofrece pyserial; sin él se muestra error de conexión.
    serial = None

BASE_DIR = Path(__file__).resolve().parent
def writable_data_dir() -> Path:
    """Elige una ruta persistente y escribible tanto instalado como en desarrollo."""
    configured = os.environ.get("DCTUNER_DATA_DIR")
    candidates = [Path(configured)] if configured else []
    candidates.extend([Path("/var/lib/dctuner"), Path.home() / ".local" / "share" / "dctuner"])
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-test"
            probe.touch(exist_ok=True)
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue
    raise RuntimeError("No hay una carpeta escribible para los datos de DCtuneRstudio")


DATA_DIR = writable_data_dir()
LOG_DIR = Path(os.environ.get("DCTUNER_LOG_DIR", str(DATA_DIR / "logs")))
MAP_DIR = Path(os.environ.get("DCTUNER_MAP_DIR", str(DATA_DIR / "maps")))
DEFAULT_PORT = os.environ.get("DCTUNER_PORT", "COM3" if os.name == "nt" else "/dev/ttyUSB0")
DEFAULT_BAUD = int(os.environ.get("DCTUNER_BAUD", "115200"))
DEFAULT_PROFILE = os.environ.get("DCTUNER_PROFILE", "megasquirt")
WEB_HOST = os.environ.get("DCTUNER_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("DCTUNER_WEB_PORT", "8080"))

logging.basicConfig(level=os.environ.get("DCTUNER_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dctuner")


@dataclass
class Telemetry:
    timestamp: float
    rpm: float = 0.0
    temperature: float = 0.0
    pressure: float = 0.0
    afr: float = 0.0
    load: float = 0.0
    advance: float = 0.0
    voltage: float = 0.0
    throttle: float = 0.0
    status: str = "offline"
    source: str = "none"


class TelemetryStore:
    """Estado compartido pequeño, con retención acotada para equipos antiguos."""

    def __init__(self, capacity: int = 900) -> None:
        self._latest = Telemetry(time.time(), status="offline")
        self._history: deque[Telemetry] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._recording = False
        self._record_file: Path | None = None
        self._record_handle: Any = None
        self._record_writer: csv.writer | None = None

    def update(self, item: Telemetry) -> None:
        with self._lock:
            self._latest = item
            self._history.append(item)
            if self._recording and self._record_writer:
                self._record_writer.writerow(telemetry_row(item))
                self._record_handle.flush()

    def latest(self) -> Telemetry:
        with self._lock:
            return self._latest

    def history(self, limit: int = 300) -> list[Telemetry]:
        with self._lock:
            return list(self._history)[-max(1, min(limit, self._history.maxlen or 900)):]

    def start_recording(self) -> Path:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        filename = LOG_DIR / f"dctuner-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        handle = filename.open("w", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        writer.writerow(telemetry_fields())
        with self._lock:
            self._recording = True
            self._record_file = filename
            self._record_handle = handle
            self._record_writer = writer
        return filename

    def stop_recording(self) -> Path | None:
        with self._lock:
            filename = self._record_file
            if self._record_handle:
                self._record_handle.flush()
                self._record_handle.close()
            self._recording = False
            self._record_file = None
            self._record_handle = None
            self._record_writer = None
            return filename

    def is_recording(self) -> bool:
        with self._lock:
            return self._recording


def telemetry_fields() -> list[str]:
    return ["timestamp", "iso_time", "rpm", "temperature", "pressure", "afr", "load", "advance", "voltage", "throttle", "status", "source"]


def telemetry_row(item: Telemetry) -> list[Any]:
    return [item.timestamp, datetime.fromtimestamp(item.timestamp, timezone.utc).isoformat(), item.rpm, item.temperature, item.pressure, item.afr, item.load, item.advance, item.voltage, item.throttle, item.status, item.source]


def telemetry_dict(item: Telemetry) -> dict[str, Any]:
    data = asdict(item)
    data["iso_time"] = datetime.fromtimestamp(item.timestamp, timezone.utc).isoformat()
    data["recording"] = store.is_recording()
    return data


class ECUTransport:
    """Transporte serie. No interpreta mapas ni envía comandos peligrosos por defecto."""

    def __init__(self, store: TelemetryStore) -> None:
        self.store = store
        self._serial: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._port = DEFAULT_PORT
        self._baud = DEFAULT_BAUD
        self._profile = DEFAULT_PROFILE
        self._last_error = "Sin conexión"
        self._lock = threading.Lock()

    def configure(self, port: str, baud: int, simulation: bool = False, profile: str = DEFAULT_PROFILE) -> None:
        safe_port = port if re.fullmatch(r"(?:/dev/tty(?:USB|ACM)[0-9]+|COM[0-9]{1,3})", port, flags=re.IGNORECASE) else DEFAULT_PORT
        with self._lock:
            self._port, self._baud = safe_port, int(baud)
            self._profile = profile if profile in {"megasquirt", "speeduino"} else "megasquirt"
        self.stop()
        self.start()

    def start(self) -> None:
        self._stop.clear()
        target = self._serial_loop
        self._thread = threading.Thread(target=target, name="dctuner-telemetry", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def status(self) -> dict[str, Any]:
        item = self.store.latest()
        return {"connected": item.status == "connected", "mode": "serie", "profile": self._profile, "port": self._port, "baud": self._baud, "serial_available": serial is not None, "last_error": self._last_error, "telemetry": telemetry_dict(item)}

    def _serial_loop(self) -> None:
        if serial is None:
            self._last_error = "Falta python3-serial; use el instalador del proyecto"
            self.store.update(Telemetry(time.time(), status="error", source="serie"))
            return
        try:
            self._serial = serial.Serial(self._port, self._baud, timeout=0.2)
            self._last_error = ""
            if self._profile == "speeduino":
                self._speeduino_loop()
                return
            while not self._stop.is_set():
                raw = self._serial.readline()
                if not raw:
                    continue
                item = parse_telemetry_line(raw.decode("ascii", errors="ignore"))
                if item:
                    item.status, item.source = "connected", self._port
                    self.store.update(item)
        except (SerialException, OSError) as exc:
            self._last_error = str(exc)
            log.warning("No se pudo abrir %s: %s", self._port, exc)
            self.store.update(Telemetry(time.time(), status="error", source="serie"))
        finally:
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

    def _speeduino_loop(self) -> None:
        """Pide la trama binaria primaria Speeduino ``A`` sin enviar ráfagas.

        Speeduino documenta una respuesta de 120 bytes y exige esperar la
        respuesta antes de enviar otra petición. Este bucle respeta ese orden.
        """
        while not self._stop.is_set():
            self._serial.write(b"A")
            payload = self._serial.read(120)
            item = parse_speeduino_realtime(payload)
            if item:
                item.status, item.source = "connected", f"Speeduino · {self._port}"
                self.store.update(item)
            else:
                self._stop.wait(0.05)

    def send_safe_command(self, command: str) -> tuple[bool, str]:
        """Solo envía cuando el usuario lo habilita explícitamente y hay serie activa."""
        command = command.strip()
        if not command or len(command) > 120 or any(ord(ch) < 32 and ch not in "\r\n\t" for ch in command):
            return False, "Comando vacío o inválido"
        if not self._serial:
            return False, "La ECU no está conectada"
        try:
            self._serial.write((command + "\r").encode("ascii", errors="strict"))
            return True, "Comando enviado"
        except (UnicodeError, OSError, SerialException) as exc:
            return False, f"No se pudo enviar: {exc}"


def parse_telemetry_line(line: str) -> Telemetry | None:
    """Acepta CSV o key=value; devuelve None para tramas desconocidas.

    Ejemplos: ``1200,86,100,14.7,35,12,13.8`` o
    ``RPM=1200,TEMP=86,MAP=100,AFR=14.7,LOAD=35,ADV=12,VOLT=13.8``.
    """
    text = line.strip()
    if not text:
        return None
    try:
        if "=" in text:
            pairs: dict[str, float] = {}
            for part in text.split(","):
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                pairs[key.strip().upper()] = float(value.strip())
            if not pairs:
                return None
            return Telemetry(time.time(), rpm=pairs.get("RPM", 0), temperature=pairs.get("TEMP", pairs.get("CLT", 0)), pressure=pairs.get("MAP", pairs.get("PRESSURE", 0)), afr=pairs.get("AFR", 0), load=pairs.get("LOAD", 0), advance=pairs.get("ADV", pairs.get("ADVANCE", 0)), voltage=pairs.get("VOLT", pairs.get("VOLTAGE", 0)), throttle=pairs.get("TPS", pairs.get("THROTTLE", 0)))
        values = [float(part.strip()) for part in text.split(",")]
        if len(values) < 7:
            return None
        values += [0] * (8 - len(values))
        return Telemetry(time.time(), rpm=values[0], temperature=values[1], pressure=values[2], afr=values[3], load=values[4], advance=values[5], voltage=values[6], throttle=values[7])
    except (TypeError, ValueError):
        return None


def parse_speeduino_realtime(payload: bytes) -> Telemetry | None:
    """Decodifica el paquete primario ``A`` de Speeduino.

    Los campos documentados son little-endian: MAP en bytes 4-5, RPM en
    bytes 14-15, avance en byte 23, TPS en byte 24, batería en décimas de
    voltio y temperatura con el offset de calibración habitual de 40.
    """
    if len(payload) < 25:
        return None
    data = list(payload)

    def u16(index: int) -> int:
        return data[index] | (data[index + 1] << 8)

    pressure = u16(4)
    rpm = u16(14)
    raw_coolant = data[7]
    temperature = raw_coolant - 40
    afr = data[10] / 10.0 if data[10] else 0.0
    return Telemetry(
        timestamp=time.time(),
        rpm=rpm,
        temperature=temperature,
        pressure=pressure,
        afr=afr,
        load=max(0.0, min(100.0, pressure / 2.5)),
        advance=float(data[23]),
        voltage=data[9] / 10.0,
        throttle=float(data[24]),
    )


store = TelemetryStore()
transport = ECUTransport(store)
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


@app.after_request
def no_cache(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index() -> Response:
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/api/health")
def health() -> Response:
    return jsonify({"ok": True, "service": "dctuner", "time": time.time(), "status": transport.status()})


@app.get("/api/telemetry")
def telemetry() -> Response:
    return jsonify({"latest": telemetry_dict(store.latest()), "history": [telemetry_dict(item) for item in store.history(int(request.args.get("limit", "300")))]})


@app.get("/api/status")
def status() -> Response:
    return jsonify(transport.status())


@app.post("/api/connection")
def connection() -> Response:
    payload = request.get_json(silent=True) or {}
    try:
        baud = int(payload.get("baud", DEFAULT_BAUD))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Baudrate inválido"}), 400
    if baud not in {9600, 19200, 38400, 57600, 115200, 230400}:
        return jsonify({"ok": False, "error": "Baudrate no permitido"}), 400
    transport.configure(str(payload.get("port", DEFAULT_PORT)), baud, False, str(payload.get("profile", DEFAULT_PROFILE)))
    return jsonify({"ok": True, "status": transport.status()})


@app.post("/api/recording")
def recording() -> Response:
    payload = request.get_json(silent=True) or {}
    if payload.get("active"):
        path = store.start_recording()
        return jsonify({"ok": True, "active": True, "file": str(path)})
    path = store.stop_recording()
    return jsonify({"ok": True, "active": False, "file": str(path) if path else None})


@app.get("/api/logs")
def logs() -> Response:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(({"name": path.name, "bytes": path.stat().st_size, "modified": path.stat().st_mtime} for path in LOG_DIR.glob("*.csv")), key=lambda entry: entry["modified"], reverse=True)
    return jsonify({"files": files[:50]})


@app.get("/api/logs/<path:name>")
def download_log(name: str) -> Response:
    safe_name = Path(name).name
    if safe_name != name or not safe_name.endswith(".csv"):
        return jsonify({"error": "Nombre de archivo inválido"}), 400
    return send_from_directory(LOG_DIR, safe_name, as_attachment=True)


@app.post("/api/command")
def command() -> Response:
    payload = request.get_json(silent=True) or {}
    ok, message = transport.send_safe_command(str(payload.get("command", "")))
    return jsonify({"ok": ok, "message": message}), 200 if ok else 409


@app.get("/api/export/current.csv")
def export_current() -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(telemetry_fields())
    for item in store.history(900):
        writer.writerow(telemetry_row(item))
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=dctuner-current.csv"})


def self_test() -> int:
    checks = [
        (parse_telemetry_line("1200,86,100,14.7,35,12,13.8") is not None, "parser CSV"),
        (parse_telemetry_line("RPM=1200,TEMP=86,MAP=100,AFR=14.7,LOAD=35,ADV=12,VOLT=13.8") is not None, "parser key=value"),
        (app.test_client().get("/api/health").status_code == 200, "endpoint health"),
        (app.test_client().get("/api/telemetry").status_code == 200, "endpoint telemetry"),
    ]
    for ok, name in checks:
        print(f"[{'OK' if ok else 'FAIL'}] {name}")
    return 0 if all(ok for ok, _ in checks) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor web local DCtuneRstudio")
    parser.add_argument("--host", default=WEB_HOST)
    parser.add_argument("--port", type=int, default=WEB_PORT)
    parser.add_argument("--serie", action="store_true", help="compatibilidad: el puente siempre usa ECU real")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    transport.start()
    log.info("DCtuneRstudio disponible en http://%s:%s (modo ECU real, perfil %s, puerto %s)", args.host, args.port, transport._profile, transport._port)
    app.run(host=args.host, port=args.port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
