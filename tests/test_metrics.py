import unittest

import pandas as pd

from src.metrics import (
    build_leaderboards,
    build_weekly_metrics,
    detect_repeat_contacts,
    get_repeat_metrics,
)


def make_ticket(ticket_id, created_at, resolved_at, category="Audio Quality", sku="VA-EB-PL1",
                customer_id="C1", status="resolved", agent_id="A1", channel="chat"):
    return {
        "ticket_id": ticket_id,
        "created_at": created_at,
        "resolved_at": resolved_at,
        "category": category,
        "product_sku": sku,
        "customer_id": customer_id,
        "status": status,
        "agent_id": agent_id,
        "channel": channel,
        "priority": "Normal",
        "transfers": 0,
    }


class RepeatContactTests(unittest.TestCase):
    def test_requires_same_customer_issue_and_prior_resolution_within_30_days(self):
        tickets = pd.DataFrame([
            make_ticket("T1", "2025-01-01", "2025-01-02"),
            make_ticket("T2", "2025-02-01", "2025-02-02"),
            make_ticket("T3", "2025-02-10", "2025-02-11", category="Billing & Payments"),
            make_ticket("T4", "2025-02-12", "2025-02-13", sku="VA-EB-PL2"),
            make_ticket("T5", "2025-03-05", "2025-03-06"),
            make_ticket("T6", "2025-03-08", "2025-03-09", customer_id="C2"),
        ])

        result = detect_repeat_contacts(tickets).set_index("ticket_id")

        self.assertTrue(result.loc["T2", "is_repeat"])
        self.assertFalse(result.loc["T3", "is_repeat"])
        self.assertFalse(result.loc["T4", "is_repeat"])
        self.assertFalse(result.loc["T5", "is_repeat"])
        self.assertFalse(result.loc["T6", "is_repeat"])

    def test_open_or_broken_prior_ticket_does_not_start_repeat_window(self):
        tickets = pd.DataFrame([
            make_ticket("T1", "2025-01-01", None, status="open"),
            make_ticket("T2", "2025-01-02", "2025-01-03"),
            make_ticket("T3", "2025-01-04", "2025-01-05"),
        ])

        result = detect_repeat_contacts(tickets).set_index("ticket_id")

        self.assertFalse(result.loc["T2", "is_repeat"])
        self.assertTrue(result.loc["T3", "is_repeat"])

    def test_empty_and_single_day_metrics_are_finite(self):
        empty = pd.DataFrame(columns=[
            "created_at", "is_repeat", "repeat_cost", "product_sku", "category"
        ])
        self.assertEqual(get_repeat_metrics(empty)["repeat_pct"], 0)
        self.assertEqual(get_repeat_metrics(empty)["quarterly_waste"], 0)

        single_day = detect_repeat_contacts(pd.DataFrame([
            make_ticket("T1", "2025-01-01", "2025-01-01"),
        ]))
        metrics = get_repeat_metrics(single_day)
        self.assertTrue(pd.notna(metrics["quarterly_waste"]))
        self.assertEqual(metrics["quarterly_waste"], 0)

    def test_weekly_metrics_use_monday_start(self):
        tickets = detect_repeat_contacts(pd.DataFrame([
            make_ticket("T1", "2025-01-05", "2025-01-06"),
            make_ticket("T2", "2025-01-06", "2025-01-07"),
        ]))

        weekly = build_weekly_metrics(tickets)

        self.assertEqual(len(weekly), 2)
        self.assertEqual(weekly.iloc[0]["week_start"], pd.Timestamp("2024-12-30"))
        self.assertEqual(weekly.iloc[1]["week_start"], pd.Timestamp("2025-01-06"))


class LeaderboardTests(unittest.TestCase):
    def test_volume_rankings_exclude_tier_two_and_use_assignment_at_ticket_date(self):
        tickets = pd.DataFrame([
            make_ticket("T1", "2025-01-01", "2025-01-02", agent_id="A1"),
            make_ticket("T2", "2025-01-01", "2025-01-04", agent_id="A2"),
        ])
        agents = pd.DataFrame([
            {"agent_id": "A1", "name": "Tier One", "team": "Frontline", "tier": 1,
             "from_date": "2024-01-01", "to_date": None},
            {"agent_id": "A1", "name": "Moved Later", "team": "Warranty", "tier": 2,
             "from_date": "2026-01-01", "to_date": None},
            {"agent_id": "A2", "name": "Tier Two", "team": "Escalations", "tier": 2,
             "from_date": "2024-01-01", "to_date": None},
        ])

        result = build_leaderboards(tickets, agents)

        self.assertEqual(result["raw_volume"]["agent_id"].tolist(), ["A1"])
        self.assertEqual(result["raw_volume"].iloc[0]["name"], "Tier One")
        self.assertEqual(result["weighted_score"]["agent_id"].tolist(), ["A1"])
        tier_two = result["team_summary"].set_index("team").loc["Escalations"]
        self.assertFalse(tier_two["volume_metric_applicable"])
        self.assertEqual(tier_two["avg_resolution_days"], 3)


if __name__ == "__main__":
    unittest.main()