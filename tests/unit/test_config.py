import os
import tempfile
import unittest
from pathlib import Path

from app.config import load_env


class ConfigTests(unittest.TestCase):
    def test_loads_env_without_overwriting_existing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "PARKING_TEST_NEW=loaded\nPARKING_TEST_EXISTING=file\n",
                encoding="utf-8",
            )
            os.environ["PARKING_TEST_EXISTING"] = "environment"
            try:
                load_env(env_file)
                self.assertEqual("loaded", os.environ["PARKING_TEST_NEW"])
                self.assertEqual("environment", os.environ["PARKING_TEST_EXISTING"])
            finally:
                os.environ.pop("PARKING_TEST_NEW", None)
                os.environ.pop("PARKING_TEST_EXISTING", None)


if __name__ == "__main__":
    unittest.main()

