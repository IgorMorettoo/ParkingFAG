import json
import unittest

from app.repository import MemoryReadingRepository
from app.web import ParkingApplication


class UserFlowSystemTests(unittest.TestCase):
    def test_user_opens_dashboard(self):
        application = ParkingApplication(MemoryReadingRepository(), ingest_key="test-key")
        response = application.dispatch("GET", "/")
        self.assertEqual(200, response.status)
        self.assertIn(b"SmartParking", response.body)

    def test_detector_publishes_and_user_reads_latest_status(self):
        application = ParkingApplication(MemoryReadingRepository(), ingest_key="test-key")
        payload = {
            "total_spaces": 2,
            "free_spaces": 1,
            "source": "camera-test",
            "spaces": [
                {"index": 1, "pixel_count": 300, "is_free": True},
                {"index": 2, "pixel_count": 1200, "is_free": False},
            ],
        }

        unauthorized = application.dispatch("POST", "/api/readings", body=json.dumps(payload).encode())
        self.assertEqual(401, unauthorized.status)

        created = application.dispatch(
            "POST",
            "/api/readings",
            {"X-Ingest-Key": "test-key"},
            json.dumps(payload).encode(),
        )
        latest = application.dispatch("GET", "/api/readings/latest")

        self.assertEqual(201, created.status)
        self.assertEqual(200, latest.status)
        reading = json.loads(latest.body)["reading"]
        self.assertEqual(1, reading["free_spaces"])
        self.assertEqual("camera-test", reading["source"])


if __name__ == "__main__":
    unittest.main()
