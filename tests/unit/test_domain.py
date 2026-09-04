import unittest

from app.domain import ParkingReading, classify_counts


class DomainTests(unittest.TestCase):
    def test_classifies_counts_at_threshold_boundary(self):
        spaces = classify_counts([100, 899, 900, 1300], threshold=900)
        self.assertEqual([True, True, False, False], [space["is_free"] for space in spaces])

    def test_calculates_occupied_spaces(self):
        reading = ParkingReading.create(total_spaces=8, free_spaces=3)
        self.assertEqual(5, reading.occupied_spaces)

    def test_rejects_impossible_free_count(self):
        with self.assertRaises(ValueError):
            ParkingReading.create(total_spaces=2, free_spaces=3)


if __name__ == "__main__":
    unittest.main()

