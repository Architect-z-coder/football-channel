"""Thin wrapper around the Claude API that returns parsed JSON."""
import json
import re

from .common import StopPipeline, log, secret


def ask_json(model: str, system: str, user: str, max_tokens: int = 8000) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=secret("ANTHROPIC_API_KEY", required=True))
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    log.info("LLM call: %s input / %s output tokens", msg.usage.input_tokens, msg.usage.output_tokens)
    return parse_json(text)


def parse_json(text: str) -> dict:
    """Accept raw JSON or JSON inside a ```json fence."""
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = fence.group(1) if fence else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise StopPipeline(f"Model did not return valid JSON: {e}") from e
