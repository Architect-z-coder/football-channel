"""Thin wrapper around the Claude API that returns parsed JSON."""
import json
import re

from .common import OUT_DIR, StopPipeline, log, secret


def ask_json(model: str, system: str, user: str, max_tokens: int = 16000) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=secret("ANTHROPIC_API_KEY", required=True))
    text_parts = []
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for chunk in stream.text_stream:
            text_parts.append(chunk)
        msg = stream.get_final_message()
    text = "".join(text_parts)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "last_llm_reply.txt").write_text(text, encoding="utf-8")
    log.info("LLM call: %s input / %s output tokens, stop: %s",
             msg.usage.input_tokens, msg.usage.output_tokens, msg.stop_reason)
    if msg.stop_reason == "max_tokens":
        raise StopPipeline("The model's reply was cut off (too long). See out/last_llm_reply.txt.")
    return parse_json(text)


def parse_json(text: str) -> dict:
    """Accept raw JSON or JSON inside a ```json fence."""
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = fence.group(1) if fence else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise StopPipeline(f"Model did not return valid JSON: {e}") from e
