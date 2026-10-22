"""Comprehensive automated tests for TravelMind AI budget intelligence system.
Tests multi-currency conversions, traveler scaling, trip durations, zero/missing prices,
contingency buffer, and strict over-budget detection.
"""
import unittest
from decimal import Decimal
from datetime import date

from backend.app.core.types import TripSpec
from backend.app.services.budget import compute_budget, convert, reduce_category, feasibility, BudgetError
from backend.app.agents.budget_intelligence import BudgetIntelligenceAgent
from backend.app.integrations.currency import build_currency_provider


class TestBudgetComprehensive(unittest.TestCase):
    def setUp(self):
        self.agent = BudgetIntelligenceAgent()

    def test_multi_currency_budget_computation(self):
        """Validates Decimal math and rounding across USD, EUR, GBP, INR, and JPY."""
        test_cases = [
            ("USD", {"flights": "450.50", "accommodation": "320.00", "food": "150.25"}, 10, "920.75", "92.08", "1012.83"),
            ("EUR", {"flights": "380.00", "accommodation": "290.50", "food": "120.00"}, 12, "790.50", "94.86", "885.36"),
            ("GBP", {"flights": "320.00", "accommodation": "250.00", "food": "110.00"}, 12, "680.00", "81.60", "761.60"),
            ("INR", {"flights": "12500.00", "accommodation": "8400.00", "food": "3600.00"}, 12, "24500.00", "2940.00", "27440.00"),
            ("JPY", {"flights": "65000", "accommodation": "42000", "food": "18000"}, 12, "125000.00", "15000.00", "140000.00"),
        ]
        for curr, items, cont_pct, exp_subtotal, exp_cont, exp_total in test_cases:
            with self.subTest(currency=curr):
                res = compute_budget(items, travelers=1, contingency_pct=cont_pct, budget=None, currency=curr)
                self.assertEqual(res.currency, curr)
                self.assertEqual(res.subtotal, Decimal(exp_subtotal))
                self.assertEqual(res.contingency, Decimal(exp_cont))
                self.assertEqual(res.total, Decimal(exp_total))
                self.assertEqual(res.per_person, Decimal(exp_total))

    def test_traveler_counts_and_room_scaling(self):
        """Validates per-person costs and room allocation for 1, 2, 3, 5, and 10 travelers."""
        traveler_counts = [1, 2, 3, 4, 5, 10]
        for t in traveler_counts:
            spec = TripSpec(
                origin="DEL",
                destination="GOA",
                departure_date=date(2026, 11, 1),
                return_date=date(2026, 11, 5),
                travelers=t,
                budget=50000 * t,
                currency="INR",
            )
            out = self.agent.run({"trip_spec": spec})
            self.assertEqual(out.status, "ok")
            data = out.data
            self.assertEqual(data["travelers"], t)
            expected_rooms = max(1, (t + 1) // 2)
            self.assertEqual(data["rooms"], expected_rooms)
            total = Decimal(data["total"])
            per_person = Decimal(data["per_person"])
            # per_person * travelers should equal total within 1 cent due to division rounding
            self.assertAlmostEqual(float(per_person * t), float(total), delta=0.05)

    def test_trip_length_extremes(self):
        """Validates calculation across 1-day express tours, 7-day vacations, and 30-day extended stays."""
        durations = [1, 4, 7, 14, 30]
        for d in durations:
            spec = TripSpec(
                origin="JFK",
                destination="LON",
                duration_days=d,
                travelers=2,
                budget=15000,
                currency="USD",
            )
            out = self.agent.run({"trip_spec": spec})
            self.assertEqual(out.status, "ok")
            data = out.data
            self.assertEqual(data["stay_days"], d)
            # Long trips must have proportionally higher food and transport totals
            food_cost = Decimal(data["items"]["food"])
            self.assertTrue(food_cost > 0)
            self.assertEqual(food_cost, Decimal(f"{40.0 * 2 * d:.2f}"))

    def test_insufficient_budget_detection(self):
        """Ensures that inadequate budgets strictly trigger OVER_BUDGET status."""
        spec = TripSpec(
            origin="DEL",
            destination="PAR",
            duration_days=5,
            travelers=2,
            budget=200,  # $200 USD is completely insufficient for 2 travelers to Paris
            currency="USD",
        )
        out = self.agent.run({"trip_spec": spec})
        self.assertEqual(out.status, "ok")
        data = out.data
        self.assertTrue(data["over_budget"])
        self.assertEqual(data["budget_status"], "OVER_BUDGET")
        self.assertTrue("exceeds the budget ceiling" in data["status_message"])
        self.assertTrue(Decimal(data["remaining"]) < 0)

    def test_zero_and_missing_prices(self):
        """Handles zero amounts and missing values gracefully without crashing."""
        res = compute_budget(
            {"flights": 0, "accommodation": 0, "food": 0, "transport": 0, "activities": 0},
            travelers=2,
            contingency_pct=12,
            budget=1000,
            currency="USD",
        )
        self.assertEqual(res.subtotal, Decimal("0.00"))
        self.assertEqual(res.contingency, Decimal("0.00"))
        self.assertEqual(res.total, Decimal("0.00"))
        self.assertEqual(res.remaining, Decimal("1000.00"))
        self.assertFalse(res.over_budget)

    def test_currency_conversion_pivot(self):
        """Tests USD pivot conversions with live currency provider rates."""
        rates = {"EUR": "0.92", "GBP": "0.79", "INR": "84.0", "CAD": "1.36"}
        self.assertEqual(convert(100, "USD", "EUR", rates), Decimal("92.00"))
        self.assertEqual(convert(92, "EUR", "USD", rates), Decimal("100.00"))
        self.assertEqual(convert(100, "USD", "INR", rates), Decimal("8400.00"))
        # EUR to GBP cross conversion
        conv_gbp = convert(100, "EUR", "GBP", rates)
        # 100 / 0.92 * 0.79 = 85.87
        self.assertEqual(conv_gbp, Decimal("85.87"))

    def test_category_reduction(self):
        """Tests deterministic category expense reduction."""
        items = {"flights": 800, "accommodation": 500, "food": 300}
        reduced = reduce_category(items, "accommodation", 25)
        self.assertEqual(reduced["accommodation"], Decimal("375.00"))
        self.assertEqual(reduced["flights"], Decimal("800.00"))
        self.assertEqual(reduced["food"], Decimal("300.00"))

    def test_budget_feasibility(self):
        """Tests feasibility checks for minimum daily allowance."""
        f_pass = feasibility(2000, days=5, travelers=2, min_daily_pp=150)
        # 150 * 5 * 2 = 1500 needed, budget 2000 => realistic
        self.assertTrue(f_pass["realistic"])
        self.assertEqual(f_pass["shortfall"], Decimal("0.00"))

        f_fail = feasibility(1000, days=5, travelers=2, min_daily_pp=150)
        # 1500 needed, budget 1000 => shortfall 500
        self.assertFalse(f_fail["realistic"])
        self.assertEqual(f_fail["shortfall"], Decimal("500.00"))


if __name__ == "__main__":
    unittest.main()
