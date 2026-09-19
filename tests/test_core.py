import tempfile
import unittest
from pathlib import Path

from dc_tuner_studio import MapData


class MapDataTests(unittest.TestCase):
    def test_msq_round_trip(self):
        original = MapData("Test", 2, 3, [[1.0, 2.5, 3.0], [4.0, 5.5, 6.0]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.msq"
            original.save(path)
            loaded = MapData.load(path)
        self.assertEqual(loaded.name, "Test")
        self.assertEqual(loaded.values, original.values)

    def test_bin_round_trip(self):
        original = MapData("Binary", 2, 2, [[1.25, 2.5], [3.75, 4.0]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.bin"
            original.save(path)
            loaded = MapData.load(path)
        self.assertEqual((loaded.rows, loaded.cols), (2, 2))
        for expected, actual in zip(sum(original.values, []), sum(loaded.values, [])):
            self.assertAlmostEqual(expected, actual, places=3)

    def test_clone_is_independent(self):
        original = MapData()
        clone = original.clone("Copy")
        clone.values[0][0] += 10
        self.assertNotEqual(original.values[0][0], clone.values[0][0])


if __name__ == "__main__":
    unittest.main()
