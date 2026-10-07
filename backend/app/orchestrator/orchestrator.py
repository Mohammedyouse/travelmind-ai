"""Dependency-aware async orchestrator: parallelism, timeouts, retries, partial results, logs."""
from __future__ import annotations
import asyncio, time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


@dataclass
class AgentSpec:
    name: str
    run: Callable[[dict], Awaitable[Any]]        # receives {"state":..., "results": {dep: output}}
    depends_on: tuple = ()
    timeout: float = 30.0
    retries: int = 1
    required: bool = False                       # if True, failure aborts dependents AND flags run failed


@dataclass
class ExecRecord:
    agent: str
    status: str          # ok | failed | timeout | skipped
    attempts: int = 0
    duration_ms: int = 0
    error: str = ""


@dataclass
class RunResult:
    results: dict = field(default_factory=dict)
    records: list = field(default_factory=list)

    @property
    def partial(self) -> bool:
        return any(r.status != "ok" for r in self.records)

    @property
    def failed_required(self) -> bool:
        return getattr(self, "_failed_required", False)


class Orchestrator:
    def __init__(self, agents: list[AgentSpec]):
        self.agents = {a.name: a for a in agents}
        self._check_graph()

    def _check_graph(self):
        for a in self.agents.values():
            for d in a.depends_on:
                if d not in self.agents:
                    raise ValueError(f"{a.name} depends on unknown agent {d}")
        state, order = {}, []
        def visit(n):
            if state.get(n) == 1:
                raise ValueError(f"dependency cycle at {n}")
            if state.get(n) == 2:
                return
            state[n] = 1
            for d in self.agents[n].depends_on:
                visit(d)
            state[n] = 2
            order.append(n)
        for n in self.agents:
            visit(n)

    async def _run_one(self, spec: AgentSpec, ctx: dict) -> tuple[Optional[Any], ExecRecord]:
        rec, t0 = ExecRecord(spec.name, "failed"), time.monotonic()
        for attempt in range(1, spec.retries + 2):
            rec.attempts = attempt
            try:
                out = await asyncio.wait_for(spec.run(ctx), spec.timeout)
                rec.status, rec.error = "ok", ""
                rec.duration_ms = int((time.monotonic() - t0) * 1000)
                return out, rec
            except asyncio.TimeoutError:
                rec.status, rec.error = "timeout", f"exceeded {spec.timeout}s"
            except Exception as e:
                rec.status, rec.error = "failed", f"{type(e).__name__}: {e}"
        rec.duration_ms = int((time.monotonic() - t0) * 1000)
        return None, rec

    async def run(self, state: dict) -> RunResult:
        rr, done, pending = RunResult(), {}, dict(self.agents)
        failed = set()
        failed_required = False
        while pending:
            ready = [a for a in pending.values() if all(d in done for d in a.depends_on)]
            if not ready:
                break
            for a in ready:
                pending.pop(a.name)
            runnable, batch = [], []
            for a in ready:
                bad = [d for d in a.depends_on if d in failed]
                if bad:
                    done[a.name] = None
                    failed.add(a.name)
                    rr.records.append(ExecRecord(a.name, "skipped", error=f"upstream failed: {bad}"))
                else:
                    runnable.append(a)
            outs = await asyncio.gather(*[
                self._run_one(a, {"state": state, "results": {d: done[d] for d in a.depends_on}})
                for a in runnable])
            for a, (out, rec) in zip(runnable, outs):
                rr.records.append(rec)
                done[a.name] = out if rec.status == "ok" else None
                if rec.status != "ok":
                    failed.add(a.name)
                if rec.status == "ok":
                    rr.results[a.name] = out
                elif a.required:
                    failed_required = True
        rr._failed_required = failed_required
        return rr
