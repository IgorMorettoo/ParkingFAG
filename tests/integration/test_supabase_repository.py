import json
import unittest

from app.domain import ParkingReading
from app.repository import SupabaseReadingRepository


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class SupabaseRepositoryIntegrationTests(unittest.TestCase):
    def test_sends_reading_to_supabase_rest_contract(self):
        captured = {}

        def transport(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            body = json.loads(request.data)
            return FakeResponse([{"id": 42, **body}])

        repository = SupabaseReadingRepository(
            "https://parking.supabase.co", "secret", transport=transport
        )
        result = repository.save(ParkingReading.create(total_spaces=3, free_spaces=1))

        self.assertEqual(42, result["id"])
        self.assertEqual("POST", captured["request"].method)
        self.assertEqual("secret", captured["request"].headers["Apikey"])
        self.assertEqual(10, captured["timeout"])


if __name__ == "__main__":
    unittest.main()
