import os
import time
import json
import anthropic
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_TRANSIENT_ERRORS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    ConnectionResetError,
    ConnectionError,
    OSError,
)


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment or .env file")
    return anthropic.Anthropic(api_key=api_key)


def load_config():
    config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
    with open(config_path) as f:
        return json.load(f)


def call_claude(
    system_prompt,
    user_message,
    model=None,
    max_tokens=16000,
    max_retries=4,
):
    """Call Claude API with streaming to handle long responses. Returns usage stats and raw text."""
    client = get_client()
    config = load_config()
    model = model or config["commentary_model"]

    for attempt in range(max_retries):
        try:
            start = time.time()

            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                thinking={"type": "disabled"},
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                response = stream.get_final_message()

            elapsed = time.time() - start

            text = response.content[0].text
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": model,
                "elapsed_seconds": round(elapsed, 2),
                "stop_reason": response.stop_reason,
            }
            return {"text": text, "usage": usage}

        except _TRANSIENT_ERRORS as e:
            if attempt >= max_retries - 1:
                raise
            wait = min(2 ** (attempt + 1) * 10, 120)
            label = type(e).__name__
            print(f"  {label}: {e}. Retrying in {wait}s ({attempt + 1}/{max_retries})...")
            time.sleep(wait)

        except anthropic.APIError as e:
            if attempt >= max_retries - 1:
                raise
            wait = 2 ** (attempt + 1) * 5
            print(f"  API error: {e}. Retrying in {wait}s ({attempt + 1}/{max_retries})...")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {max_retries} retries")
