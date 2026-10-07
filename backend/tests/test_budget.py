import unittest
from decimal import Decimal
from backend.app.services import budget as b


class BudgetTests(unittest.TestCase):
    def test_total_with_contingency(self):
        r = b.compute_budget({"flights": "400.10", "accommodation": 350, "food": 140.555}, travelers=2,
                             contingency_pct=10, budget=1000)
        self.assertEqual(r.subtotal, Decimal("890.66"))
        self.assertEqual(r.contingency, Decimal("89.07"))
        self.assertEqual(r.total, Decimal("979.73"))
        self.assertEqual(r.remaining, Decimal("20.27"))
        self.assertFalse(r.over_budget)
        self.assertEqual(r.per_person, Decimal("489.87"))

    def test_over_budget(self):
        r = b.compute_budget({"flights": 1200}, budget=1000, contingency_pct=0)
        self.assertTrue(r.over_budget)
        self.assertEqual(r.remaining, Decimal("-200.00"))

    def test_no_float_drift(self):
        r = b.compute_budget({"a": 0.1, "b": 0.2}, contingency_pct=0)
        self.assertEqual(r.total, Decimal("0.30"))

    def test_validation(self):
        with self.assertRaises(b.BudgetError): b.compute_budget({"a": -1})
        with self.assertRaises(b.BudgetError): b.compute_budget({"a": 1}, travelers=0)
        with self.assertRaises(b.BudgetError): b.compute_budget({"a": 1}, contingency_pct=150)

    def test_convert_requires_supplied_rates(self):
        self.assertEqual(b.convert(100, "USD", "EUR", {"EUR": "0.9"}), Decimal("90.00"))
        self.assertEqual(b.convert(90, "EUR", "USD", {"EUR": "0.9"}), Decimal("100.00"))
        self.assertEqual(b.convert(5, "USD", "USD", {}), Decimal("5.00"))
        with self.assertRaises(b.BudgetError): b.convert(1, "USD", "INR", {})

    def test_reduce_hotel_20_percent(self):
        out = b.reduce_category({"accommodation": "500", "food": "100"}, "accommodation", 20)
        self.assertEqual(out["accommodation"], Decimal("400.00"))
        self.assertEqual(out["food"], Decimal("100.00"))
        with self.assertRaises(b.BudgetError): b.reduce_category({"food": 1}, "hotel", 20)

    def test_feasibility(self):
        f = b.feasibility(1200, days=7, travelers=1, min_daily_pp=200)
        self.assertFalse(f["realistic"]); self.assertEqual(f["shortfall"], Decimal("200.00"))
        self.assertTrue(b.feasibility(1200, 7, 1, 100)["realistic"])


if __name__ == "__main__":
    unittest.main()
