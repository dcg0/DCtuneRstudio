import unittest

from dc_tuner_studio import estimate_horsepower


class HorsepowerEstimateTests(unittest.TestCase):
    def test_estimate_is_reproducible_from_inputs(self):
        sample = {"rpm": 1800, "map": 44.0, "afr": 15.0}
        value = estimate_horsepower(sample, displacement_l=2.0, ve=0.85)
        self.assertGreater(value, 0)
        self.assertAlmostEqual(value, estimate_horsepower(sample, 2.0, 0.85), places=8)

    def test_more_airflow_increases_estimate(self):
        low = estimate_horsepower({"rpm": 2000, "map": 35, "afr": 14.7}, 2.0, 0.85)
        high = estimate_horsepower({"rpm": 2000, "map": 70, "afr": 14.7}, 2.0, 0.85)
        self.assertGreater(high, low)


if __name__ == "__main__":
    unittest.main()
