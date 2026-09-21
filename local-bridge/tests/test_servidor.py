#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dctuner_web"))
import servidor  # noqa: E402


class ParserTests(unittest.TestCase):
    def test_csv_frame(self):
        item = servidor.parse_telemetry_line("1200,86,100,14.7,35,12,13.8,18")
        self.assertIsNotNone(item)
        self.assertEqual(item.rpm, 1200)
        self.assertEqual(item.temperature, 86)
        self.assertEqual(item.throttle, 18)

    def test_key_value_frame(self):
        item = servidor.parse_telemetry_line("RPM=1500,TEMP=90,MAP=105,AFR=14.3,LOAD=40,ADV=16,VOLT=13.9,TPS=22")
        self.assertIsNotNone(item)
        self.assertEqual(item.rpm, 1500)
        self.assertEqual(item.afr, 14.3)
        self.assertEqual(item.throttle, 22)

    def test_invalid_frame(self):
        self.assertIsNone(servidor.parse_telemetry_line("not-a-frame"))
        self.assertIsNone(servidor.parse_telemetry_line("1,2"))

    def test_speeduino_primary_realtime_packet(self):
        packet = bytearray(120)
        packet[4:6] = (100).to_bytes(2, "little")
        packet[7] = 126  # 86 °C after the documented calibration offset.
        packet[9] = 138  # 13.8 V.
        packet[10] = 147  # 14.7 AFR.
        packet[14:16] = (1800).to_bytes(2, "little")
        packet[23] = 18
        packet[24] = 22
        item = servidor.parse_speeduino_realtime(bytes(packet))
        self.assertIsNotNone(item)
        self.assertEqual(item.rpm, 1800)
        self.assertEqual(item.pressure, 100)
        self.assertEqual(item.temperature, 86)
        self.assertAlmostEqual(item.afr, 14.7)
        self.assertAlmostEqual(item.voltage, 13.8)
        self.assertEqual(item.throttle, 22)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = servidor.app.test_client()
        servidor.transport.stop()
        servidor.transport._simulation = False
        servidor.transport.start()

    def tearDown(self):
        servidor.transport.stop()

    def test_health_and_telemetry(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        response = self.client.get("/api/telemetry?limit=2")
        self.assertEqual(response.status_code, 200)
        self.assertIn("latest", response.get_json())

    def test_connection_rejects_invalid_baud(self):
        response = self.client.post("/api/connection", json={"baud": 12345})
        self.assertEqual(response.status_code, 400)

    def test_connection_accepts_real_serial_port_configuration(self):
        response = self.client.post("/api/connection", json={"port": "COM7", "baud": 115200, "simulation": False, "profile": "megasquirt"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"]["port"], "COM7")

    def test_command_blocks_without_real_ecu(self):
        response = self.client.post("/api/command", json={"command": "status"})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["ok"])

    def test_recording_writes_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            original = servidor.LOG_DIR
            servidor.LOG_DIR = Path(directory)
            try:
                start = self.client.post("/api/recording", json={"active": True})
                self.assertTrue(start.get_json()["active"])
                stop = self.client.post("/api/recording", json={"active": False})
                self.assertFalse(stop.get_json()["active"])
                self.assertTrue(Path(stop.get_json()["file"]).exists())
            finally:
                servidor.LOG_DIR = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
