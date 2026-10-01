import unittest

import pandas as pd

from src.evaluate import evaluate_labels


class EvaluationTests(unittest.TestCase):
    def test_empty_annotation_template_reports_no_accuracy(self):
        frame = pd.DataFrame({
            "gold_category": ["", ""],
            "predicted_category": ["Delivery & Shipping", "Other"],
            "gold_repeat": ["", ""],
            "predicted_repeat": ["false", "true"],
        })

        result = evaluate_labels(frame)

        self.assertEqual(result["category"]["n"], 0)
        self.assertIsNone(result["category"]["accuracy"])
        self.assertEqual(result["repeat_flag"]["n"], 0)
        self.assertIsNone(result["repeat_flag"]["f1"])

    def test_scores_only_completed_labels(self):
        frame = pd.DataFrame({
            "gold_category": ["Delivery & Shipping", "Billing & Payments", ""],
            "predicted_category": ["Delivery & Shipping", "Returns & Refunds", "Other"],
            "gold_repeat": ["true", "false", ""],
            "predicted_repeat": ["true", "true", "false"],
        })

        result = evaluate_labels(frame)

        self.assertEqual(result["category"], {"n": 2, "accuracy": 0.5})
        self.assertEqual(result["repeat_flag"]["n"], 2)
        self.assertEqual(result["repeat_flag"]["precision"], 0.5)


if __name__ == "__main__":
    unittest.main()