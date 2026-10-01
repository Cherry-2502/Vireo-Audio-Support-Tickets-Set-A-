import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.classify import TAXONOMY, classify_batch


class FakeModels:
    def __init__(self, response):
        self.response = response

    def generate_content(self, **kwargs):
        return SimpleNamespace(text=json.dumps(self.response))


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


class ClassifierTests(unittest.TestCase):
    def test_valid_response_is_returned(self):
        ticket = {"ticket_id": "T1", "customer_message": "No sound", "agent_notes": ""}
        expected = [{
            "ticket_id": "T1",
            "category": TAXONOMY[0],
            "repeat_complaint_flag": False,
        }]

        result = classify_batch([ticket], client=FakeClient(expected))

        self.assertEqual(result, expected)

    def test_missing_key_is_reported_before_network_call(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                classify_batch([{"ticket_id": "T1"}])

    def test_invalid_category_is_rejected(self):
        ticket = {"ticket_id": "T1"}
        response = [{
            "ticket_id": "T1",
            "category": "Not in taxonomy",
            "repeat_complaint_flag": False,
        }]

        with self.assertRaisesRegex(ValueError, "unsupported category"):
            classify_batch([ticket], client=FakeClient(response))

    def test_duplicate_ticket_ids_are_rejected(self):
        tickets = [{"ticket_id": "T1"}, {"ticket_id": "T2"}]
        duplicate_response = [{
            "ticket_id": "T1", "category": TAXONOMY[0], "repeat_complaint_flag": False,
        }] * 2

        with self.assertRaisesRegex(ValueError, "exactly one result"):
            classify_batch(tickets, client=FakeClient(duplicate_response))


if __name__ == "__main__":
    unittest.main()