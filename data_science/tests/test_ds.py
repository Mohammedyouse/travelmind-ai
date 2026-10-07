import unittest
from data_science.pipelines.recommender import Candidate, Profile, rank, score
from data_science.pipelines.optimizer import Option, optimize


class RecommenderTests(unittest.TestCase):
    def setUp(self):
        self.p = Profile(budget=100, interests=frozenset({"history", "food"}), traveler_type="solo", month=11)
        self.a = Candidate("hagia", 20, frozenset({"history"}), rating=4.8, distance_km=2)
        self.b = Candidate("mall", 20, frozenset({"shopping"}), rating=4.8, distance_km=2)
        self.c = Candidate("palace", 300, frozenset({"history", "food"}), rating=4.9, distance_km=1)

    def test_interest_match_wins(self):
        r = rank([self.b, self.a], self.p)
        self.assertEqual(r[0]["id"], "hagia")

    def test_over_budget_penalised(self):
        s = {x["id"]: x["score"] for x in rank([self.a, self.c], self.p)}
        self.assertGreater(s["hagia"], s["palace"] - 0.2)
        self.assertLess(score(self.c, self.p)["breakdown"]["budget"], score(self.a, self.p)["breakdown"]["budget"])

    def test_missing_data_not_scored_as_zero(self):
        s = score(Candidate("x", 10, frozenset({"history", "food"})), self.p)
        self.assertIn("rating", s["missing"]); self.assertNotIn("rating", s["breakdown"])
        self.assertAlmostEqual(sum(s["breakdown"].values()), s["score"], places=3)
        self.assertGreater(s["score"], 0.8)

    def test_deterministic(self):
        self.assertEqual(rank([self.a, self.b, self.c], self.p), rank([self.c, self.b, self.a], self.p))


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.f = [Option("cheap_fl", 300, 0.3, 14), Option("direct_fl", 700, 0.9, 6)]
        self.h = [Option("hostel", 150, 0.3), Option("hotel4", 450, 0.85)]

    def test_three_plans_differ(self):
        o = optimize(self.f, self.h)
        self.assertEqual((o["budget"]["flight"], o["budget"]["hotel"]), ("cheap_fl", "hostel"))
        self.assertEqual((o["comfort"]["flight"], o["comfort"]["hotel"]), ("direct_fl", "hotel4"))

    def test_budget_constraint(self):
        o = optimize(self.f, self.h, budget=800)
        self.assertTrue(o["budget"]["within_budget"]); self.assertTrue(o["balanced"]["within_budget"])
        self.assertLessEqual(o["balanced"]["cost"], 800)

    def test_infeasible_budget_returns_none(self):
        self.assertIsNone(optimize(self.f, self.h, budget=100)["budget"])

    def test_empty_inputs(self):
        with self.assertRaises(ValueError): optimize([], self.h)


if __name__ == "__main__":
    unittest.main()
