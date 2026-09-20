import tempfile
import unittest
from pathlib import Path

from ini_loader import load_definition


class IniLoaderTests(unittest.TestCase):
    def test_reads_metadata_and_sections(self):
        content = '[MegaTune]\nsignature = "demo ECU"\nversionInfo = "1.2"\n[TunerStudio]\niniSpecVersion = 3.64\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.ini"
            path.write_text(content, encoding="utf-8")
            definition = load_definition(path)
        self.assertEqual(definition.signature, "demo ECU")
        self.assertEqual(definition.version, "1.2")
        self.assertEqual(definition.ini_spec_version, "3.64")
        self.assertTrue(definition.has_section("TunerStudio"))

    def test_rejects_empty_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.ini"
            path.write_text("; comment only\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_definition(path)


if __name__ == "__main__":
    unittest.main()
