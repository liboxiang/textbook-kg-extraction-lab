import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / "data" / ".test_active_experiment.json"


class ExperimentCheckpointTests(unittest.TestCase):
    def tearDown(self):
        for path in (TEST_PATH, TEST_PATH.with_suffix(TEST_PATH.suffix + ".tmp")):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def test_round_trip_uses_only_supported_state(self):
        from services.experiment_checkpoint import load_checkpoint, save_checkpoint

        save_checkpoint(
            {
                "kp_id": "KP1",
                "stage1_confirmed": True,
                "stage1_resolved": {"knowledge_units": []},
                "unrelated_widget": "discard me",
            },
            TEST_PATH,
        )
        self.assertEqual(
            load_checkpoint(TEST_PATH),
            {
                "kp_id": "KP1",
                "stage1_confirmed": True,
                "stage1_resolved": {"knowledge_units": []},
            },
        )

    def test_clear_and_corrupt_file_are_safe(self):
        from services.experiment_checkpoint import clear_checkpoint, load_checkpoint

        TEST_PATH.write_text("not json", encoding="utf-8")
        self.assertEqual(load_checkpoint(TEST_PATH), {})
        clear_checkpoint(TEST_PATH)
        self.assertFalse(TEST_PATH.exists())


if __name__ == "__main__":
    unittest.main()
