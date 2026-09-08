import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class HumanAnalysisIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.face = json.loads((ROOT / "summary.json").read_text())
        cls.preservation = json.loads((ROOT / "summary-preservation.json").read_text())
        with (ROOT / "decoded-face.csv").open() as file:
            cls.face_rows = list(csv.DictReader(file))
        with (ROOT / "decoded-preservation.csv").open() as file:
            cls.preservation_rows = list(csv.DictReader(file))

    def test_complete_unique_candidate_sets(self):
        self.assertEqual(len(self.face_rows), 16)
        self.assertEqual(len(self.preservation_rows), 16)
        self.assertEqual(len({row["candidate"] for row in self.face_rows}), 16)
        self.assertEqual(
            {row["candidate"] for row in self.face_rows},
            {row["candidate"] for row in self.preservation_rows},
        )

    def test_no_selected_threshold_in_current_summary(self):
        comparison = self.face["threshold_free"]
        self.assertFalse(any("threshold" in key for key in comparison))
        for key, value in comparison.items():
            if key.endswith("_auc"):
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_saved_auc_and_paired_counts(self):
        comparison = self.face["threshold_free"]
        self.assertAlmostEqual(comparison["fixed_ssim_auc"], 0.9523809523809523)
        self.assertAlmostEqual(comparison["aligned_ssim_spearman"], 0.7335956466074456)
        paired = comparison["paired_sequential_vs_end_regeneration"]
        self.assertEqual(paired["n"], 7)
        self.assertEqual(paired["aligned_mae_sequential_higher"], 7)
        self.assertEqual(paired["aligned_ssim_sequential_higher"], 7)
        self.assertEqual(paired["aligned_lpips_sequential_higher"], 7)

    def test_human_face_and_preservation_pairing(self):
        paired = self.preservation["paired_with_face"]
        self.assertEqual(paired["n"], 16)
        self.assertEqual(paired["clear_face_equals_failed_preservation"], 16)
        self.assertEqual(paired["rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
