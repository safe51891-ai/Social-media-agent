"""The only module that talks to OpenAI. Everything else calls these three functions."""
import base64
import os

from openai import OpenAI

from agent.config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout, max_retries=3)
    return _client


def ask(instructions: str, prompt: str, web: bool = False) -> str:
    """Text generation. web=True lets the model use OpenAI's hosted web search."""
    extra = {"tools": [{"type": "web_search"}]} if web else {}
    response = _get_client().responses.create(
        model=settings.text_model,
        instructions=instructions,
        input=prompt,
        **extra,
    )
    return response.output_text


def image(prompt: str, out_path: str) -> str:
    """Generate one square image and save it to out_path."""
    result = _get_client().images.generate(model=settings.image_model, prompt=prompt, size="1024x1024")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(result.data[0].b64_json))
    return out_path
