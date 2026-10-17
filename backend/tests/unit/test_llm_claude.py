"""T-031: the Claude drafter with a fake SDK client (no real API calls in tests)."""

import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from app.integrations.llm.base import Fact, NarrativeUnavailable
from app.integrations.llm.claude import ClaudeNarrativeDrafter


class FakeMessages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def drafter(result: Any) -> tuple[ClaudeNarrativeDrafter, FakeMessages]:
    messages = FakeMessages(result)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ClaudeNarrativeDrafter("key", "claude-opus-5-5", 10, client=client), messages


def response(text: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)]
    )


FACTS = [Fact("F1", "[CUSTOMER] requested a transfer of ₹1,000.")]


def test_parses_structured_output_and_sends_pseudonymised_facts() -> None:
    d, messages = drafter(
        response(json.dumps({"narrative_en": "Hi [CUSTOMER].", "facts_used": ["F1"]}))
    )
    out = d.draft(FACTS)
    assert (out.narrative, out.facts_used) == ("Hi [CUSTOMER].", ["F1"])
    kwargs = messages.kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["fallbacks"] == "default"
    assert "<facts>" in kwargs["messages"][0]["content"]


@pytest.mark.parametrize(
    ("result", "reason"),
    [
        (response("", stop_reason="refusal"), "LLM_REFUSED"),
        (response("{}", stop_reason="max_tokens"), "LLM_INCOMPLETE"),
        (response("not json"), "LLM_BAD_OUTPUT"),
        (anthropic.APITimeoutError(request=httpx2.Request("POST", "https://x")), "LLM_TIMEOUT"),
        (
            anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x")),
            "LLM_UNREACHABLE",
        ),
    ],
)
def test_failures_become_fallback_reasons(result: Any, reason: str) -> None:
    d, _ = drafter(result)
    with pytest.raises(NarrativeUnavailable) as exc:
        d.draft(FACTS)
    assert exc.value.reason == reason
