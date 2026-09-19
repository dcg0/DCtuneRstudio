import unittest

from protocols import Elm327Adapter, MegaSquirtAdapter, SpeeduinoAdapter


class ProtocolTests(unittest.TestCase):
    def test_profiles_identify_without_write_capability(self):
        for adapter in (SpeeduinoAdapter(), MegaSquirtAdapter(), Elm327Adapter()):
            self.assertTrue(adapter.identify_command())
            self.assertFalse(adapter.write_capability())

    def test_normalized_csv_frame(self):
        frame = SpeeduinoAdapter().parse_line("1200,42.5,18,86,14.7,13.8")
        self.assertIsNotNone(frame)
        self.assertEqual(frame.rpm, 1200)
        self.assertEqual(frame.map_kpa, 42.5)

    def test_invalid_frame_is_ignored(self):
        self.assertIsNone(Elm327Adapter().parse_line("NO DATA"))
        self.assertIsNone(Elm327Adapter().parse_line("1200,nan,18,86,14.7,13.8"))


if __name__ == "__main__":
    unittest.main()
