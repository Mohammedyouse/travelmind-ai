import asyncio, json, unittest
from datetime import date
from backend.app.core.types import TripSpec, ValidationError
from backend.app.integrations.base import (AmadeusFlightProvider, UnconfiguredFlightProvider,
                                           build_flight_provider)
from backend.app.llm.base import GeminiClient, LLMClient, LLMGateway, LLMResponse, LLMError, extract_json
from backend.app.orchestrator.orchestrator import AgentSpec, Orchestrator


class TestTripSpec(unittest.TestCase):
    def test_missing_fields(self):
        s = TripSpec(origin="PNQ", destination="IST")
        self.assertIn("budget", s.missing())
        self.assertIn("departure_date_or_duration", s.missing())

    def test_complete(self):
        s = TripSpec.from_dict({"origin": "PNQ", "destination": "IST", "budget": 1200, "currency": "USD",
                                "duration_days": 7})
        self.assertEqual(s.missing(), [])

    def test_rejects_bad(self):
        for bad in ({"budget": -5}, {"currency": "usd"}, {"travelers": 0}, {"bogus": 1},
                    {"departure_date": "2026-11-10", "return_date": "2026-11-01"},
                    {"departure_date": "not-a-date"}):
            with self.assertRaises(ValidationError, msg=str(bad)):
                TripSpec.from_dict(bad)

    def test_roundtrip(self):
        d = {"origin": "PNQ", "destination": "IST", "departure_date": "2026-11-01", "budget": 1200.0}
        self.assertEqual(TripSpec.from_dict(d).to_dict()["departure_date"], "2026-11-01")


def fake_amadeus(calls):
    offer = {"id": "1", "price": {"grandTotal": "512.40", "currency": "USD"},
             "itineraries": [{"duration": "PT11H", "segments": [
                 {"carrierCode": "TK", "departure": {"at": "2026-11-01T02:00"}, "arrival": {"at": "2026-11-01T08:00"}},
                 {"carrierCode": "TK", "departure": {"at": "2026-11-01T10:00"}, "arrival": {"at": "2026-11-01T13:00"}}]}]}
    def t(method, url, headers, body, timeout):
        calls.append(url)
        if "oauth2/token" in url:
            return 200, json.dumps({"access_token": "tok"}).encode()
        return 200, json.dumps({"data": [offer]}).encode()
    return t


class TestProviders(unittest.TestCase):
    def test_unconfigured_is_honest(self):
        r = build_flight_provider({}).search("PNQ", "IST", "2026-11-01")
        self.assertEqual(r.status, "unconfigured")
        self.assertIsNone(r.data)

    def test_amadeus_normalises(self):
        calls = []
        p = AmadeusFlightProvider("id", "sec", transport=fake_amadeus(calls))
        r = p.search("PNQ", "IST", "2026-11-01", adults=2)
        self.assertTrue(r.ok)
        o = r.data[0]
        self.assertEqual((o["price"], o["stops"], o["carriers"]), (512.40, 1, ["TK"]))
        self.assertIn("adults=2", calls[-1])

    def test_amadeus_http_error(self):
        def t(m, u, h, b, to):
            return (200, b'{"access_token":"x"}') if "oauth2" in u else (500, b"")
        r = AmadeusFlightProvider("i", "s", transport=t).search("A", "B", "2026-01-01")
        self.assertEqual(r.status, "error")

    def test_amadeus_auth_fail(self):
        r = AmadeusFlightProvider("i", "s", transport=lambda *a: (401, b"")).search("A", "B", "2026-01-01")
        self.assertEqual(r.status, "error")

    def test_amadeus_network_exception(self):
        def t(*a): raise OSError("down")
        r = AmadeusFlightProvider("i", "s", transport=t).search("A", "B", "2026-01-01")
        self.assertEqual(r.status, "error")
        self.assertIn("OSError", r.message)


class Scripted(LLMClient):
    name = "scripted"
    def __init__(self, outs): self.outs, self.n = list(outs), 0
    def generate(self, prompt, *, system="", json_mode=False):
        self.n += 1
        o = self.outs.pop(0)
        if isinstance(o, Exception): raise o
        return LLMResponse(o, "scripted", 10, 5)


class TestLLM(unittest.TestCase):
    def gw(self, *clients, **k): return LLMGateway(list(clients), sleep=lambda s: None, **k)

    def test_retry_on_invalid_json_then_ok(self):
        c = Scripted(["not json", '```json\n{"origin":"PNQ","destination":"IST","budget":900}\n```'])
        spec = self.gw(c).structured("x", TripSpec.from_dict)
        self.assertEqual(spec.destination, "IST")
        self.assertEqual(c.n, 2)

    def test_schema_violation_retried(self):
        c = Scripted(['{"budget": -1}', '{"budget": 5}'])
        self.assertEqual(self.gw(c).structured("x", TripSpec.from_dict).budget, 5)

    def test_fallback_provider(self):
        bad, good = Scripted([LLMError("down")] * 3), Scripted(['{"budget": 7}'])
        self.assertEqual(self.gw(bad, good).structured("x", TripSpec.from_dict).budget, 7)

    def test_all_fail(self):
        with self.assertRaises(LLMError):
            self.gw(Scripted(["bad"] * 3), retries=2).structured("x", TripSpec.from_dict)

    def test_usage_and_cost(self):
        g = self.gw(Scripted(['{"budget": 1}']))
        g.structured("x", TripSpec.from_dict)
        self.assertEqual((g.usage.prompt_tokens, g.usage.completion_tokens), (10, 5))
        self.assertAlmostEqual(g.usage.cost(1.0, 2.0), 20 / 1e6)

    def test_gemini_parsing(self):
        body = {"candidates": [{"content": {"parts": [{"text": "hi"}]}}],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 1}}
        seen = {}
        def t(m, u, h, b, to): seen.update(h=h, b=json.loads(b)); return 200, json.dumps(body).encode()
        r = GeminiClient("KEY", transport=t).generate("p", system="s", json_mode=True)
        self.assertEqual((r.text, r.prompt_tokens), ("hi", 3))
        self.assertEqual(seen["h"]["x-goog-api-key"], "KEY")
        self.assertIn("systemInstruction", seen["b"])

    def test_gemini_http_error(self):
        with self.assertRaises(LLMError):
            GeminiClient("k", transport=lambda *a: (429, b"")).generate("p")


class TestOrchestrator(unittest.TestCase):
    def run_(self, o, state=None): return asyncio.run(o.run(state or {}))

    def test_dependencies_and_context(self):
        async def a(ctx): return 1
        async def b(ctx): return ctx["results"]["a"] + 1
        r = self.run_(Orchestrator([AgentSpec("b", b, ("a",)), AgentSpec("a", a)]))
        self.assertEqual(r.results, {"a": 1, "b": 2})
        self.assertFalse(r.partial)

    def test_parallel_independent(self):
        async def slow(ctx): await asyncio.sleep(0.2); return 1
        o = Orchestrator([AgentSpec(n, slow) for n in "xyz"])
        import time; t = time.monotonic(); self.run_(o)
        self.assertLess(time.monotonic() - t, 0.5)

    def test_failure_gives_partial_and_skips_dependents(self):
        async def boom(ctx): raise RuntimeError("x")
        async def ok(ctx): return "fine"
        async def dep(ctx): return "never"
        r = self.run_(Orchestrator([AgentSpec("f", boom, retries=0), AgentSpec("g", ok),
                                    AgentSpec("d", dep, ("f",))]))
        st = {x.agent: x.status for x in r.records}
        self.assertEqual(st, {"f": "failed", "g": "ok", "d": "skipped"})
        self.assertEqual(r.results, {"g": "fine"})
        self.assertTrue(r.partial)

    def test_timeout(self):
        async def hang(ctx): await asyncio.sleep(5)
        r = self.run_(Orchestrator([AgentSpec("h", hang, timeout=0.05, retries=0)]))
        self.assertEqual(r.records[0].status, "timeout")

    def test_retry_then_success(self):
        n = {"c": 0}
        async def flaky(ctx):
            n["c"] += 1
            if n["c"] < 3: raise RuntimeError("t")
            return "ok"
        r = self.run_(Orchestrator([AgentSpec("f", flaky, retries=2)]))
        self.assertEqual((r.records[0].status, r.records[0].attempts), ("ok", 3))

    def test_none_output_is_not_failure(self):
        async def none(ctx): return None
        async def dep(ctx): return "ran"
        r = self.run_(Orchestrator([AgentSpec("n", none), AgentSpec("d", dep, ("n",))]))
        self.assertEqual(r.results["d"], "ran")

    def test_required_failure_flag(self):
        async def boom(ctx): raise RuntimeError
        r = self.run_(Orchestrator([AgentSpec("r", boom, retries=0, required=True)]))
        self.assertTrue(r.failed_required)

    def test_cycle_and_unknown_dep(self):
        async def n(ctx): pass
        with self.assertRaises(ValueError):
            Orchestrator([AgentSpec("a", n, ("b",)), AgentSpec("b", n, ("a",))])
        with self.assertRaises(ValueError):
            Orchestrator([AgentSpec("a", n, ("zzz",))])


if __name__ == "__main__":
    unittest.main()
