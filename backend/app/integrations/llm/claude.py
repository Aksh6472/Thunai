"""Claude narrative drafter (FR-21). Off by default (THUNAI_LLM_ENABLED); tests never call it.

Pseudonymised facts in, structured JSON out (output_config json_schema). Any error, refusal,
truncation or malformed output raises NarrativeUnavailable and the caller uses the template.
"""

import json
import logging
from pathlib import Path
from typing import Any

import anthropic

from app.integrations.llm.base import Draft, Fact, NarrativeUnavailable

logger = logging.getLogger(__name__)

PROMPT = (Path(__file__).parent / "prompts" / "report_narrative_v1.md").read_text(encoding="utf-8")
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "narrative_en": {"type": "string"},
            "facts_used": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["narrative_en", "facts_used"],
        "additionalProperties": False,
    },
}


class ClaudeNarrativeDrafter:
    def __init__(
        self, api_key: str, model: str, timeout_seconds: float, client: Any = None
    ) -> None:
        self._model = model
        # SDK retries once (AI_DESIGN §12.2); timeout in seconds.
        self._client: Any = client or anthropic.Anthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=1
        )

    def draft(self, facts: list[Fact]) -> Draft:
        output_config: dict[str, Any] = {"effort": "low", "format": OUTPUT_SCHEMA}
        facts_json = json.dumps([{"id": f.id, "fact": f.text} for f in facts], ensure_ascii=False)
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=2000,
                system=PROMPT,
                messages=[{"role": "user", "content": f"<facts>\n{facts_json}\n</facts>"}],
                output_config=output_config,
                # Server-side refusal fallback: a declined request is re-run on a fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APITimeoutError:
            raise NarrativeUnavailable("LLM_TIMEOUT") from None
        except anthropic.RateLimitError:
            raise NarrativeUnavailable("LLM_RATE_LIMITED") from None
        except anthropic.APIStatusError as exc:
            logger.warning("llm.api_error", extra={"status": exc.status_code})
            raise NarrativeUnavailable("LLM_API_ERROR") from None
        except anthropic.APIConnectionError:
            raise NarrativeUnavailable("LLM_UNREACHABLE") from None

        if response.stop_reason == "refusal":
            raise NarrativeUnavailable("LLM_REFUSED")
        if response.stop_reason != "end_turn":
            raise NarrativeUnavailable("LLM_INCOMPLETE")
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        try:
            data = json.loads(text)
            return Draft(
                narrative=str(data["narrative_en"]), facts_used=[str(x) for x in data["facts_used"]]
            )
        except (ValueError, KeyError, TypeError):
            raise NarrativeUnavailable("LLM_BAD_OUTPUT") from None
