"""Provider-independent LLM layer: structured-output validation, retries, fallback, cost tracking."""
from __future__ import annotations
import json, re, time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional
from ..integrations.base import Transport, urllib_transport


class LLMError(RuntimeError): ...


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(ABC):
    name: str
    @abstractmethod
    def generate(self, prompt: str, *, system: str = "", json_mode: bool = False) -> LLMResponse: ...


class GeminiClient(LLMClient):
    """Gemini REST client. Not verified against the live API in the build sandbox."""
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", transport: Transport = urllib_transport,
                 timeout: float = 30.0):
        self.key, self.model, self.t, self.timeout = api_key, model, transport, timeout

    def generate(self, prompt, *, system="", json_mode=False):
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"] = {"responseMimeType": "application/json"}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        st, raw = self.t("POST", url, {"Content-Type": "application/json", "x-goog-api-key": self.key},
                         json.dumps(body).encode(), self.timeout)
        if st != 200:
            raise LLMError(f"gemini HTTP {st}")
        d = json.loads(raw)
        try:
            text = d["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise LLMError("gemini returned no candidates")
        u = d.get("usageMetadata", {})
        return LLMResponse(text, self.model, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))


@dataclass
class UsageTracker:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    failures: int = 0

    def add(self, r: LLMResponse):
        self.prompt_tokens += r.prompt_tokens
        self.completion_tokens += r.completion_tokens
        self.calls += 1

    def cost(self, usd_per_1m_in: float, usd_per_1m_out: float) -> float:
        """Caller supplies current pricing; none is hardcoded here."""
        return (self.prompt_tokens * usd_per_1m_in + self.completion_tokens * usd_per_1m_out) / 1e6


def extract_json(text: str):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return json.loads(t)


class LLMGateway:
    """Tries clients in order; validates structured output; retries on invalid output."""
    def __init__(self, clients: list[LLMClient], *, retries: int = 2, sleep: Callable = time.sleep,
                 backoff: float = 0.5):
        if not clients:
            raise ValueError("at least one LLM client required")
        self.clients, self.retries, self.sleep, self.backoff = clients, retries, sleep, backoff
        self.usage = UsageTracker()

    def structured(self, prompt: str, validate: Callable[[dict], object], *, system: str = ""):
        """`validate` must raise on bad data (e.g. TripSpec.from_dict). Returns validate(...) result."""
        last: Optional[Exception] = None
        for c in self.clients:
            for attempt in range(self.retries + 1):
                try:
                    r = c.generate(prompt, system=system, json_mode=True)
                    self.usage.add(r)
                    return validate(extract_json(r.text))
                except Exception as e:
                    self.usage.failures += 1
                    last = e
                    if attempt < self.retries:
                        self.sleep(self.backoff * (2 ** attempt))
        raise LLMError(f"all providers failed: {last}")
